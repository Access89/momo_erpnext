# -*- coding: utf-8 -*-
# Copyright (c) 2021, Isaac larbi and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
import frappe

class TransactionResponse(Document):
	def validate(self):
		# frappe.log_error("function called", "Transaction Response validate function")
		return True

