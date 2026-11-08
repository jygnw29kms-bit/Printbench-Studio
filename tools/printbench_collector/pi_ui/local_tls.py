"""PRINTBENCH local HTTPS identity. Private keys never enter the project tree."""
from __future__ import annotations
import datetime, ipaddress, os, pathlib, socket, subprocess
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

BASE=pathlib.Path(os.environ.get('LOCALAPPDATA',str(pathlib.Path.home()/'AppData'/'Local')))/'PRINTBENCH'/'mobile'
CA_KEY=BASE/'ca-private.pem'
CA_CERT=BASE/'ca.cer'
KEY=BASE/'server-private.pem'
CERT=BASE/'server-cert.pem'
PUBLIC=pathlib.Path(__file__).resolve().parent/'static'/'PRINTBENCH-Local-CA.cer'

def private_acl(path):
    try:
        user=os.environ.get('USERNAME','')
        if user:
            subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',f'{user}:F','SYSTEM:F','Administrators:F'],
                           capture_output=True,check=False)
    except Exception:
        pass

def pem_key(key):
    return key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())

def save(path,data,secret=False):
    path.write_bytes(data)
    if secret:
        try:os.chmod(path,0o600)
        except OSError:pass
        if os.name=='nt':private_acl(path)

def addresses():
    result={'127.0.0.1'}
    if os.environ.get('PRINTBENCH_LAN_IP'):
        result.add(os.environ['PRINTBENCH_LAN_IP'])
    for host in [socket.gethostname(),socket.getfqdn()]:
        try:
            for item in socket.getaddrinfo(host,None,family=socket.AF_INET):
                result.add(item[4][0])
        except OSError:pass
    # Public-facing NIC only, never a guessed external address.
    return sorted(ipaddress.ip_address(x) for x in result if x and not x.startswith('169.254.'))

def ensure_certificates():
    BASE.mkdir(parents=True,exist_ok=True)
    today=datetime.datetime.now(datetime.timezone.utc)
    if CA_KEY.exists() and CA_CERT.exists():
        ca_key=serialization.load_pem_private_key(CA_KEY.read_bytes(),password=None)
        ca=x509.load_der_x509_certificate(CA_CERT.read_bytes())
    else:
        ca_key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'PRINTBENCH Private LAN CA')])
        ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(today-datetime.timedelta(days=1))
            .not_valid_after(today+datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,
                key_cert_sign=True,crl_sign=True,key_agreement=False,content_commitment=False,
                data_encipherment=False,encipher_only=False,decipher_only=False),critical=True)
            .sign(ca_key,hashes.SHA256()))
        save(CA_KEY,pem_key(ca_key),True)
        save(CA_CERT,ca.public_bytes(serialization.Encoding.DER))
    ip_sans=addresses()
    # Regenerate on new IP or within 30 days of leaf expiry.
    valid=False
    if CERT.exists() and KEY.exists():
        try:
            old=x509.load_pem_x509_certificate(CERT.read_bytes())
            existing={str(x.value) for x in old.extensions.get_extension_for_class(x509.SubjectAlternativeName).value if isinstance(x,x509.IPAddress)}
            expiry=old.not_valid_after_utc
            valid=expiry>today+datetime.timedelta(days=30) and set(map(str,ip_sans)).issubset(existing)
        except Exception:pass
    if not valid:
        leaf_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        leaf_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'PRINTBENCH LAN')])
        leaf=(x509.CertificateBuilder().subject_name(leaf_name).issuer_name(ca.subject)
            .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(today-datetime.timedelta(days=1))
            .not_valid_after(today+datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(x) for x in ip_sans]),critical=False)
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=True,key_cert_sign=False,
                crl_sign=False,key_agreement=False,content_commitment=False,data_encipherment=False,
                encipher_only=False,decipher_only=False),critical=True)
            .sign(ca_key,hashes.SHA256()))
        save(KEY,pem_key(leaf_key),True)
        save(CERT,leaf.public_bytes(serialization.Encoding.PEM))
    PUBLIC.write_bytes(CA_CERT.read_bytes())
    return CERT,KEY,ip_sans

if __name__=='__main__':
    _,_,ips=ensure_certificates()
    print('PRINTBENCH certificate prepared for: '+', '.join(map(str,ips)))
    print('CA certificate for iPhone: '+str(PUBLIC))
    print('CA private key stored outside repository.')
