from auth.authentication import create_user
from pipeline import process_new_transaction
from reports.pdf_report import generate_investigation_pdf


def test_pdf_report_generated_and_downloaded(client):
    user = create_user("pdfuser@example.com", "Password@123", "PDF User")
    admin = create_user("pdfadmin@example.com", "Password@123", "PDF Admin", "ADMIN")
    for amount in (500, 800, 900):
        process_new_transaction(
            user["id"],
            {
                "amount": amount,
                "transaction_type": "UPI",
                "beneficiary": "ABC",
                "location": "Hyderabad",
                "device_id": "DEVICE_01",
                "ip_address": "192.168.1.10",
                "transaction_time": "11:00 AM",
                "is_international": 0,
                "is_new_device": 0,
                "is_new_beneficiary": 0,
            },
        )
    result = process_new_transaction(
        user["id"],
        {
            "transaction_id": "PDFHIGH",
            "amount": 150000,
            "transaction_type": "TRANSFER",
            "beneficiary": "Rahul",
            "location": "Mumbai",
            "device_id": "DEVICE_NEW_99",
            "ip_address": "192.168.1.50",
            "transaction_time": "02:30 AM",
            "is_international": 1,
            "is_new_device": 1,
            "is_new_beneficiary": 1,
        },
    )
    inv = result["investigation"]
    assert inv
    path = generate_investigation_pdf(inv["id"])
    assert path.exists()
    assert path.read_bytes()[:4] == b"%PDF"

    client.post(
        "/login",
        data={"email": "pdfadmin@example.com", "password": "Password@123"},
        follow_redirects=True,
    )
    resp = client.get(f"/report/{inv['id']}/download")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"
    reports_page = client.get("/reports")
    assert reports_page.status_code == 200
    assert b"PDFHIGH" in reports_page.data
    assert admin["id"]
