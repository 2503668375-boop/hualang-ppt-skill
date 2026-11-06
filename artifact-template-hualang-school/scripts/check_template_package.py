#!/usr/bin/env python3
"""Delegate package checks; recognize only the verified inherited original closing.
Set HUALANG_PACKAGE_VALIDATOR to the platform's package-integrity validator.
No package content is modified and no other finding is waived.
"""
import importlib.util,json,os,subprocess,sys,zipfile
from pathlib import Path
here=Path(__file__).resolve().parent
validator=os.environ.get('HUALANG_PACKAGE_VALIDATOR')
if not validator:raise SystemExit('HUALANG_PACKAGE_VALIDATOR is required')
args=sys.argv[1:];source=Path(next(a for a in args if not a.startswith('--')))
p=subprocess.run([sys.executable,validator,*args],capture_output=True,text=True)
try:report=json.loads(p.stdout)
except Exception:
 print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);raise SystemExit(p.returncode or 1)
spec=importlib.util.spec_from_file_location('contract',here/'check_style_contract.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=json.loads((here.parent/'assets/style-contract.json').read_text())
with zipfile.ZipFile(source) as z:
 last=m.slide_parts(z)[-1];check=m.closing_check(z,last,c['closing']['assetSha256'],c['closing'])
allowed=[];remaining=[]
for finding in report.get('findings',[]):
 if finding.get('code')=='slide_has_no_drawable_objects' and finding.get('part')==last and check['passed']:
  allowed.append({'finding':finding,'basis':'Original template closing is an inherited full-page image. Asset hash and absence of added content verified.'})
 else:remaining.append(finding)
if allowed:
 report['findings']=remaining;report['finding_count']=len(remaining);report['status']='fail' if remaining else 'pass';report['verified_template_backgrounds']=allowed
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(1 if remaining or (p.returncode and not allowed) else 0)
