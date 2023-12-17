#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random

class Account(object):
    account_counter=0
    
    def __init__(self, firstname, lastname, email):
        self.firstname = firstname[0].upper()+firstname[1:].lower()
        self.lastname = lastname[0].upper()+lastname[1:].lower()
        Account.account_counter += 1
        self.accountNumber = random.randint(10000000, 99999999)
        self.pin = self.generate_pin()
        self.currentbalance = 0
        self.savingbalance = 0
        self.email=email
        
        with open("customers.txt", 'a') as file_object:
            file_object.write(f"{self.firstname} {self.lastname} {self.accountNumber} {self.pin} {self.currentbalance} {self.savingbalance} {self.email}\n")
        
    def generate_pin(self):
        
        first_initial = self.firstname[0].upper()
        last_initial = self.lastname[0].upper()

        # Calculating values for pin components
        total_name_length = len(self.firstname)+len(self.lastname)
        first_initial_position = ord(first_initial) - ord('A') + 1
        last_initial_position = ord(last_initial) - ord('A') + 1

        # Creating the pin by concatenating components
        pin = f"{first_initial}{last_initial}-{first_initial_position:02d}-{last_initial_position:02d}-{total_name_length:02d}"

        return pin

