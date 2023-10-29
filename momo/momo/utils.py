#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import requests
import frappe
import base64
import hashlib
import hmac
import json
from frappe import _

#The function runs every minute. 
def update_paid_requests():
    frappe.log_error('Function started','START: update_paid_requests')
    print("---------------------------------------------------------------------------------------------------------------")
    print("START: update_paid_requests")
    print("---------------------------------------------------------------------------------------------------------------\n")
    transaction_doctype = 'Transaction Response'

    paystack_settings = frappe.get_list('Paystack Settings', fields=['name'])
    for setting in paystack_settings:
        setting_doc = frappe.get_doc('Paystack Settings', setting['name'])
        secret_key = setting_doc.get_password(fieldname='secret_key', raise_exception=False)

        # Fetch list of Transactions
        transactions = frappe.get_list(transaction_doctype, fields=['*'],filters= { 'status':'initiated'}) 
        print("---------------------------------------------------------------------------------------------------------------")
        print("Initiated Transactions: "+str(len(transactions)) + "\n" + str(transactions)) 
        print("---------------------------------------------------------------------------------------------------------------\n")
        
        for transaction in transactions:
            if transaction['status'] ==  'Initiated' :
                # Ask Paystack for status of payment request
                url = "https://api.paystack.co/transaction/verify/"+ transaction["reference"]
                headers = {
                    "Authorization": "Bearer " + secret_key,
                    "Cache-Control": "no-cache",
                    "Content-Type": "application/json"
                }
                r = requests.get(url, headers=headers)
                response = r.json()
                
                print("---------------------------------------------------------------------------------------------------------------")
                print(json.dumps(response))
                print("---------------------------------------------------------------------------------------------------------------\n")

                api_call_successful = response['status']
                if not api_call_successful:
                    print("---------------------------------------------------------------------------------------------------------------")
                    print("Paystack Verify API Call: Failed" + response["message"])
                    print("---------------------------------------------------------------------------------------------------------------\n")
                    frappe.log_error(response["message"], "API Call Failed")
                else:
                    print("---------------------------------------------------------------------------------------------------------------")
                    print("Paystack Verify API Call: Successful")
                    print("Saving response as "+ transaction_doctype)
                    print("---------------------------------------------------------------------------------------------------------------\n")
                    
                    tr_doc = frappe.get_doc(transaction_doctype, transaction['name'])
                    tr_doc.amount = response['data']['amount']/100
                    tr_doc.paid_at = response['data']['paid_at']
                    tr_doc.created_at = response['data']['created_at']
                    tr_doc.gateway_response = response['data']['gateway_response']
                    tr_doc.channel = response['data']['channel']
                    tr_doc.currency = response['data']['currency']
                    tr_doc.sales_order_id = response['data']['metadata']['sales_order_id']

                    payment_successful = response['data']['status'] == "success"
                    payment_failed = response['data']['status'] == "failed"
                    payment_abandoned = response['data']['status'] == "abandoned"
                    payment_reversed = response['data']['status'] == "reversed"

                    if payment_successful:
                        print("---------------------------------------------------------------------------------------------------------------")
                        print("Payment Successful")
                        print("---------------------------------------------------------------------------------------------------------------\n")
                        tr_doc.status = "Paid"
                        pr_doc = frappe.get_doc('Payment Request',response['data']['metadata']['payment_request_id'])
                        pr_doc.create_payment_entry(submit=True)
                    elif payment_failed:
                        print("---------------------------------------------------------------------------------------------------------------")
                        print("Payment Failed")
                        print("---------------------------------------------------------------------------------------------------------------\n")
                        tr_doc.status = "Failed"
                    elif payment_abandoned:
                        print("---------------------------------------------------------------------------------------------------------------")
                        print("Payment Abandoned/Pending")
                        print("---------------------------------------------------------------------------------------------------------------\n")
                        
                        tr_doc.status = "Abandoned"
                    elif payment_reversed:
                        print("---------------------------------------------------------------------------------------------------------------")
                        print("Payment Reversed")
                        print("---------------------------------------------------------------------------------------------------------------\n")
                        tr_doc.status = "Reversed"

                    tr_doc.save()
                
                    
@frappe.whitelist(allow_guest=True)
def paystack_webhook():
    
    # use postman to send a simulated paystack success event and write the logic to update the appropriate sale order.
    # write another function to run and release held up stocks after a set time
    # Return res 200 for paystack to stop sending webhook event
    
    # if(frappe.request and frappe.request.data):
    #     res = json.loads(frappe.request.data)
    #     frappe.log_error(res, 'charge.success')
    #     # if(res["event"] == "charge.success"):
    #     #     frappe.log_error(res["data"], 'charge.success')
    #     #     frappe.log_error(res["data"]["metadata"], 'metadata')
    #     #     frappe.local.response['http_status_code'] = 200
    #     # else:
    #     #     pass
    # else:
    #     return frappe.throw("No data")
    if(frappe.request.data):
        frappe.log_error(str(frappe.request.data), "POST request log")
    frappe.local.response['http_status_code'] = 200

    frappe.log_error('hello','hi')
    # woocommerce_settings = frappe.get_doc("Woocommerce Settings")
    if frappe.request and frappe.request.data:
        frappe.log_error(str(frappe.request.data),
                         'update_order utils called')
    return "done"
    # ....verify_request()
    # ....try:
    # ........order = json.loads(frappe.request.data)
    # ....except ValueError:
    # ........#woocommerce returns 'webhook_id=value' for the first request which is not JSON
    # ........order = frappe.request.data
    # ....event = frappe.get_request_header("X-Wc-Webhook-Event")

    # else:
    # ....return "success"

    # if event == "updated":
    # ....frappe.log_error(order,'Order Updated')


@frappe.whitelist(allow_guest=True)
def verify_payment_callback(**args):
    # Get transaction reference from callback url
    args = frappe._dict(args)
    # frappe.log_error(str(args), "VerifyPaymentCallback: args dict")

@frappe.whitelist(allow_guest=True)
def verify_request():
    woocommerce_settings = frappe.get_doc('Woocommerce Settings')
    sig = \
        base64.b64encode(hmac.new(woocommerce_settings.secret.encode('utf8'
                         ), frappe.request.data,
                         hashlib.sha256).digest())

    if frappe.request.data \
        and frappe.get_request_header('X-Wc-Webhook-Signature') \
        and not sig \
        == bytes(frappe.get_request_header('X-Wc-Webhook-Signature'
                 ).encode()):
        frappe.throw(_('Unverified Webhook Data'))
    frappe.set_user(woocommerce_settings.creation_user)
