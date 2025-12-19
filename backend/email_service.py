import os

class EmailService:
    def __init__(self):
        pass

    def send_lead_notification(self, lead_data, pdf_path):
        """
        Simulates sending an email to the Admin and the Client.
        """
        print("="*60)
        print(" [EMAIL SERVICE MOCK] SENDING EMAIL")
        print("="*60)
        print(f" To: {lead_data['email']}")
        print(f" Subject: Your Project Vision - Lynch Landscape")
        print(f" Attachment: {pdf_path}")
        print("-" * 20)
        print(f" AND ADMIN ALERT SENT TO: info@lynchlandscape.com")
        print(f" High Priority Lead: {lead_data['name']}")
        print(f" Timeline: {lead_data['timeline']}")
        print(f" Budget: {lead_data['budget']}")
        print("="*60)
        return True
