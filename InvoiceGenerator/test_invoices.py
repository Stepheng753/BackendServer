import io
import unittest
import os
import json
from flask import Flask
from InvoiceGenerator.db import (
    init_db,
    get_senders,
    add_sender,
    get_sender_by_id,
    update_sender,
    set_default_sender,
    delete_sender,
    get_clients,
    add_client,
    get_client_by_id,
    update_client,
    delete_client,
    add_preset,
    get_presets_by_client,
    delete_preset,
    generate_next_invoice_number,
    create_invoice,
    get_invoices,
    get_invoice_by_id,
    update_invoice,
    update_invoice_status,
    duplicate_invoice,
    delete_invoice,
    get_invoices_summary
)
from InvoiceGenerator.pdf import generate_invoice_pdf
from InvoiceGenerator.routes import invoice_bp


class InvoiceGeneratorTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.app = Flask(__name__, template_folder="templates")
        cls.app.config["TESTING"] = True
        cls.app.register_blueprint(invoice_bp)
        cls.client = cls.app.test_client()

    def test_01_sender_crud(self):
        senders = get_senders()
        self.assertGreaterEqual(len(senders), 1)

        # Add new sender
        new_sender_id = add_sender(
            name="Crossroads Tutoring Services",
            email="crossroads@example.com",
            phone="858-555-1234",
            address="San Diego, CA",
            payment_instructions="Zelle to stepheng753@gmail.com"
        )
        self.assertIsNotNone(new_sender_id)

        s = get_sender_by_id(new_sender_id)
        self.assertEqual(s["name"], "Crossroads Tutoring Services")
        self.assertEqual(s["email"], "crossroads@example.com")

        # Update sender
        update_sender(new_sender_id, name="Crossroads Tutoring LLC", email="billing@crossroads.com")
        s2 = get_sender_by_id(new_sender_id)
        self.assertEqual(s2["name"], "Crossroads Tutoring LLC")
        self.assertEqual(s2["email"], "billing@crossroads.com")

        # Set default
        set_default_sender(new_sender_id)
        s3 = get_sender_by_id(new_sender_id)
        self.assertEqual(s3["is_default"], 1)

        # Cleanup
        delete_sender(new_sender_id)
        self.assertIsNone(get_sender_by_id(new_sender_id))

    def test_02_client_and_preset_crud(self):
        # Add client
        client_id = add_client(
            name="Alice Walker",
            email="alice@example.com",
            phone="619-555-4321",
            address="789 Pacific Beach Dr, San Diego, CA",
            notes="SAT Math tutoring"
        )
        self.assertIsNotNone(client_id)
        c = get_client_by_id(client_id)
        self.assertEqual(c["name"], "Alice Walker")

        # Add preset
        items = [{"description": "SAT Math Tutoring (2 hrs)", "quantity": 2, "unit_price": 65.0}]
        preset_id = add_preset(
            client_id=client_id,
            preset_name="Weekly 2hr SAT Tutoring",
            default_due_days=7,
            items=items,
            notes="Please send confirmation upon payment."
        )
        self.assertIsNotNone(preset_id)

        presets = get_presets_by_client(client_id)
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0]["preset_name"], "Weekly 2hr SAT Tutoring")
        self.assertEqual(len(presets[0]["items"]), 1)

        # Delete preset and client
        delete_preset(preset_id)
        self.assertEqual(len(get_presets_by_client(client_id)), 0)

        delete_client(client_id)
        self.assertIsNone(get_client_by_id(client_id))

    def test_03_invoice_lifecycle_and_calculations(self):
        client_id = add_client(
            name="Bob Martin",
            email="bob@example.com",
            address="100 Ocean Blvd"
        )

        inv_num = generate_next_invoice_number()
        self.assertTrue(inv_num.startswith("INV-"))

        # Create invoice
        data = {
            "invoice_number": inv_num,
            "client_id": client_id,
            "client_name": "Bob Martin",
            "issue_date": "2026-09-26",
            "due_date": "2026-10-10",
            "status": "draft",
            "discount_amount": 10.0,
            "tax_rate": 5.0,
            "items": [
                {"description": "Calculus Tutoring (3 hrs)", "quantity": 3, "unit_price": 70.0},
                {"description": "Practice Materials Booklet", "quantity": 1, "unit_price": 20.0}
            ]
        }
        # Subtotal: 3 * 70 (210) + 1 * 20 (20) = 230
        # Discount: 10 => Discounted: 220
        # Tax: 5% of 220 = 11
        # Total: 220 + 11 = 231
        inv_id = create_invoice(data)
        self.assertIsNotNone(inv_id)

        inv = get_invoice_by_id(inv_id)
        self.assertEqual(inv["subtotal"], 230.0)
        self.assertEqual(inv["discount_amount"], 10.0)
        self.assertEqual(inv["total_amount"], 231.0)
        self.assertEqual(len(inv["items"]), 2)

        # Update status
        self.assertTrue(update_invoice_status(inv_id, "sent"))
        self.assertEqual(get_invoice_by_id(inv_id)["status"], "sent")

        # Duplicate
        dup_id = duplicate_invoice(inv_id)
        self.assertIsNotNone(dup_id)
        dup_inv = get_invoice_by_id(dup_id)
        self.assertEqual(dup_inv["status"], "draft")
        self.assertEqual(dup_inv["total_amount"], 231.0)
        self.assertNotEqual(dup_inv["invoice_number"], inv["invoice_number"])

        # Summary check
        summary = get_invoices_summary()
        self.assertGreaterEqual(summary["total_invoiced"], 231.0)

        # Cleanup
        delete_invoice(inv_id)
        delete_invoice(dup_id)
        delete_client(client_id)

    def test_04_pdf_generation_bytes(self):
        sample_invoice = {
            "invoice_number": "INV-TEST-001",
            "sender_name_snapshot": "Stephen Giang",
            "sender_info": {"email": "stepheng753@gmail.com", "address": "San Diego, CA"},
            "client_name_snapshot": "Test Client",
            "client_info": {"email": "test@example.com"},
            "issue_date": "2026-09-26",
            "due_date": "2026-10-10",
            "status": "sent",
            "subtotal": 100.0,
            "discount_amount": 0.0,
            "tax_rate": 0.0,
            "total_amount": 100.0,
            "payment_instructions": "Zelle: stepheng753@gmail.com",
            "notes": "Thank you!",
            "items": [{"description": "Physics Tutoring", "quantity": 1, "unit_price": 100.0, "amount": 100.0}]
        }
        buf = generate_invoice_pdf(sample_invoice)
        self.assertIsInstance(buf, io.BytesIO)
        content = buf.getvalue()
        self.assertGreater(len(content), 1000)
        self.assertTrue(content.startswith(b"%PDF"))

    def test_05_api_endpoints(self):
        # Summary
        resp = self.client.get("/api/invoices/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("total_invoiced", data)
        self.assertIn("outstanding", data)
        self.assertIn("paid", data)

        # Next number
        resp = self.client.get("/api/invoices/next-number")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("next_number", resp.get_json())

        # Senders
        resp = self.client.get("/api/invoices/senders")
        self.assertEqual(resp.status_code, 200)

        # Clients
        resp = self.client.get("/api/invoices/clients")
        self.assertEqual(resp.status_code, 200)

        # Invoices list
        resp = self.client.get("/api/invoices")
        self.assertEqual(resp.status_code, 200)

        # HTML UI Page
        resp = self.client.get("/invoices")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invoice Generator & History", resp.data)


if __name__ == "__main__":
    unittest.main()
