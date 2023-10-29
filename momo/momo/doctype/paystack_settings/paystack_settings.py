from __future__ import unicode_literals
import frappe
from frappe import _
import json
import requests
# from frappe.integrations.utils import create_payment_gateway
from payments.payments.utils import create_payment_gateway

from frappe.model.document import Document
from frappe.utils import call_hook_method, nowdate
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice, make_delivery_note
# import random
# import string
# from paystack.resource import TransactionResource

SUPPORTED_CURRENCIES = ['GHS']


class PaystackSettings(Document):
    supported_currencies = SUPPORTED_CURRENCIES

    def on_update(self):
        name = 'Paystack-{0}'.format(self.gateway_name)
        create_payment_gateway(
            name,
            settings='Paystack Settings',
            controller=self.gateway_name
        )
        call_hook_method('payment_gateway_enabled', gateway=name)

    def validate_transaction_currency(self, currency):
        if currency not in self.supported_currencies:
            frappe.throw(
                _('{currency} is not supported by Paystack at the moment.').format(currency))

    def get_payment_url(self, **kwargs):
        secret_key = self.get_password(
            fieldname='secret_key', raise_exception=False)
        amount = kwargs.get('amount') * 100
        description = kwargs.get('description')
        payment_request_id = kwargs.get('reference_docname')
        email = kwargs.get('payer_email')

        url = "https://api.paystack.co/transaction/initialize/"
        # metadata = {
        #     'payment_request': kwargs.get('order_id'),
        #     'customer_name': kwargs.get('payer_name')
        # }
        headers = {
            "Authorization": "Bearer " + secret_key,
            "Cache-Control": "no-cache",
            "Content-Type": "application/json"
        }
        
        pr_doc = frappe.get_doc("Payment Request", payment_request_id)

        data = {
            "amount": amount,
            "currency": "GHS",
            "email": email,
            "metadata": {
                "payment_request_id": payment_request_id,
                "sales_order_id": pr_doc.reference_name,
                "custom_fields":[
                    {
                        "display_name":"Payment Request ID",
                        "variable_name":"pr_id",
                        "value": payment_request_id
                    },
                    {
                        "display_name":"Sales Order ID",
                        "variable_name":"so_id",
                        "value": pr_doc.reference_name
                    }
                ]
            }
        }

        r = requests.post(url, data=json.dumps(data), headers=headers)
        res_json = r.json()

        successful = res_json['status'] == True
        failed = res_json['status'] == False
        

        if(successful):
            #Get data from response
            authorization_url = res_json['data']['authorization_url']
            access_code = res_json['data']['access_code']
            reference = res_json['data']['reference']
            # payment_request_doc = frappe.get_doc("Payment Request", payment_request_id)

            #Save authorization url, access code, reference and payment request in Transaction Response doctype
            try:
                transaction_response_doc = frappe.get_doc({
                    'doctype': 'Transaction Response',
                    'authorization_url':authorization_url,
                    'access_code': access_code,
                    'reference': reference,
                    'payment_request':payment_request_id,
                    'status':'Initiated'
                })

                transaction_response_doc.insert(ignore_permissions=True)
                frappe.db.commit()
                # frappe.log_error("Successful", "Error: Saving Transaction Response to DB")

            except Exception as e:
                s = str(e)
                frappe.log_error(s, "Error: Saving Transaction Response to DB")

            return authorization_url
        elif(failed):
            frappe.log_error(str(res_json),"get_payment_url failed")

