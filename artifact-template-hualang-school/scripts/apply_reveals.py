#!/usr/bin/env python3
"""Add native click-to-appear steps to named PPTX shapes. Standard library only.

Input and output must differ. Existing timing is rejected. --state produces a
static preview at a zero-based click count (across each animated slide).
"""
import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as E

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS={'p':P,'a':A,'r':R}
for prefix,uri in NS.items(): E.register_namespace(prefix,uri)

def sub(parent,tag,**attrs):
    return E.SubElement(parent,'{'+P+'}'+tag,{k:str(v) for k,v in attrs.items()})

def timing(groups,kinds):
    node=E.Element('{'+P+'}timing'); count=iter(range(1,1000000))
    def tn(parent,**kw): return sub(parent,'cTn',id=next(count),**kw)
    root=tn(sub(sub(node,'tnLst'),'par'),dur='indefinite',restart='never',nodeType='tmRoot')
    seq=sub(sub(root,'childTnLst'),'seq',concurrent='1',nextAc='seek')
    main=tn(seq,dur='indefinite',nodeType='mainSeq'); mainlist=sub(main,'childTnLst')
    for group in groups:
        click=tn(sub(mainlist,'par'),fill='hold')
        sub(sub(click,'stCondLst'),'cond',delay='indefinite')
        wrapper=tn(sub(sub(click,'childTnLst'),'par'),fill='hold')
        sub(sub(wrapper,'stCondLst'),'cond',delay='0')
        effects=sub(wrapper,'childTnLst')
        for i,spid in enumerate(group):
            effect=tn(sub(effects,'par'),presetID='1',presetClass='entr',presetSubtype='0',
                fill='hold',grpId='0',nodeType='clickEffect' if i==0 else 'withEffect')
            sub(sub(effect,'stCondLst'),'cond',delay='0')
            behavior=sub(sub(sub(effect,'childTnLst'),'set'),'cBhvr')
            setting=tn(behavior,dur='1',fill='hold')
            sub(sub(setting,'stCondLst'),'cond',delay='0')
            sub(sub(behavior,'tgtEl'),'spTgt',spid=spid)
            sub(sub(behavior,'attrNameLst'),'attrName').text='style.visibility'
            # p:to is a sibling of p:cBhvr under p:set.
            set_node=list(effect.find('p:childTnLst',NS))[0]
            sub(sub(set_node,'to'),'strVal',val='visible')
    for container,event in [('prevCondLst','onPrev'),('nextCondLst','onNext')]:
        cond=sub(sub(seq,container),'cond',evt=event,delay='0')
        sub(sub(cond,'tgtEl'),'sldTgt')
    builds=sub(node,'bldLst')
    for group in groups:
        for spid in group:
            if kinds[spid]=='graphicFrame': sub(sub(builds,'bldGraphic',spid=spid,grpId='0'),'bldAsOne')
            else: sub(builds,'bldP',spid=spid,grpId='0',animBg='1')
    return node

def transform(source,destination,manifest,state=None):
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve(): raise ValueError('Input and output must differ.')
    if destination.exists(): raise ValueError('Output exists; choose a new destination.')
    if state is not None and state<0: raise ValueError('State must be nonnegative.')
    if manifest.get('schemaVersion')!=1 or manifest.get('effect')!='appear': raise ValueError('Unsupported manifest.')
    reports=[]; replacements={}; slide_indexes=set()
    with zipfile.ZipFile(source) as z:
        rel=E.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        targets={r.get('Id'):r.get('Target') for r in rel}
        pres=E.fromstring(z.read('ppt/presentation.xml'))
        slide_parts=[]
        for s in pres.find('p:sldIdLst',NS):
            t=targets[s.get('{'+R+'}id')]
            slide_parts.append(t.lstrip('/') if t.startswith('/') else 'ppt/'+t)
        for entry in manifest.get('slides',[]):
            index=entry['slide']
            if not isinstance(index,int) or not 1<=index<=len(slide_parts) or index in slide_indexes:
                raise ValueError('Invalid or duplicate slide index.')
            slide_indexes.add(index); part=slide_parts[index-1]; root=E.fromstring(z.read(part))
            if root.find('p:timing',NS) is not None: raise ValueError(f'Slide {index} already has timing.')
            tree=root.find('p:cSld/p:spTree',NS); objects={}
            for obj in tree:
                nv=obj.find('.//p:cNvPr',NS)
                if nv is not None: objects.setdefault(nv.get('name'),[]).append((nv.get('id'),obj))
            used=set(); groups=[]; hidden=[]; kinds={}
            for step_i,step in enumerate(entry['steps']):
                group=[]
                if not step.get('objects'): raise ValueError('Empty reveal step.')
                for name in step['objects']:
                    if name in used or len(objects.get(name,[]))!=1: raise ValueError('Missing, duplicate or reused object: '+name)
                    used.add(name); spid,obj=objects[name][0]
                    kind=obj.tag.rsplit('}',1)[-1]
                    if kind not in ['sp','pic','graphicFrame']: raise ValueError('Unsupported reveal target: '+name)
                    kinds[spid]=kind
                    group.append(spid)
                    if state is not None and step_i>=state: hidden.append(obj)
                groups.append(group)
            if state is None:
                t=timing(groups,kinds)
                # CT_Slide order: cSld, clrMapOvr, transition, timing, extLst.
                ext=root.find('p:extLst',NS)
                root.insert(list(root).index(ext),t) if ext is not None else root.append(t)
            else:
                for obj in hidden: tree.remove(obj)
            replacements[part]=E.tostring(root,encoding='utf-8',xml_declaration=True)
            reports.append({'slide':index,'steps':len(groups),'objects':sum(map(len,groups)),'state':state})
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist(): out.writestr(item,replacements.get(item.filename,z.read(item.filename)))
    return reports

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path);ap.add_argument('manifest',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--state',type=int);a=ap.parse_args()
    print(json.dumps(transform(a.source,a.output,json.loads(a.manifest.read_text()),a.state),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
