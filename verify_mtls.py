import asyncio
import ssl
from pathlib import Path
from bindu.security.certificates import generate_self_signed_cert, create_client_cert

async def verify_mtls():
    print("🔒 Generating test certificates...")
    certs_dir = Path("certs")
    certs_dir.mkdir(exist_ok=True)
    
    # Generate CA
    ca_cert, ca_key = generate_self_signed_cert(
        "Bindu Root CA", certs_dir, "ca.crt", "ca.key"
    )
    
    # Generate Server Cert
    server_cert, server_key = generate_self_signed_cert(
        "localhost", certs_dir, "server.crt", "server.key"
    )
    
    # Generate Client Cert
    client_cert, client_key = create_client_cert(
        ca_cert, ca_key, "Bindu Client", certs_dir, "client.crt", "client.key"
    )
    
    print(f"✅ Certificates generated in '{certs_dir.absolute()}'")
    print("\nTo test:")
    print("1. Start server with: SECURITY__MTLS_ENABLED=True SECURITY__REQUIRE_CLIENT_CERT=True uvicorn bindu.server:app")
    print("2. Run client check (simulated context creation):")
    
    try:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(server_cert))
        ssl_ctx.load_cert_chain(certfile=str(client_cert), keyfile=str(client_key))
        # Disable hostname check for localhost self-signed
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        print("✅ SSL Context created successfully with client certs!")
    except Exception as e:
        print(f"❌ Failed to create SSL context: {e}")

if __name__ == "__main__":
    asyncio.run(verify_mtls())
