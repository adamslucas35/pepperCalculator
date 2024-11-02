import streamlit as st
import pandas as pd
import sqlite3

from datetime import datetime, timedelta
from decimal import Decimal

class PepperDeal: 
    def __init__(self, brand, face_value, multiplier, reg_rate, bonus_date):
        self.brand = brand
        self.face_value = face_value
        self.multiplier = multiplier
        self.reg_rate = reg_rate
        self.bonus_date = bonus_date
        self.base_coins_per_dollar = 20
        self.coins_per_dollar_redemption = 2000

    def calculate_pepper_value(self):
        # ''' Calculate value of pepper coins'''
        total_coins = (
            self.face_value * self.base_coins_per_dollar * self.multiplier
        )

        return Decimal(total_coins) / self.coins_per_dollar_redemption
    
class Deal:
    def __init__(self, 
                 face_value: Decimal, 
                 buyer_rate: Decimal, 
                 pepper_deal: PepperDeal, 
                 payment_delay_weeks: int = 2):
        self.face_value = face_value
        self.buyer_rate = buyer_rate
        self.pepper_deal = pepper_deal
        self.payment_delay_weeks = payment_delay_weeks
    
    def calculate_delay_bonus(self): 
        #Calculate bonus rate on payment delays
        additional_weeks = self.payment_delay_weeks
        if additional_weeks == 2: 
            return Decimal('0.0038')
        elif additional_weeks == 4:
            return Decimal('0.0075')
        elif additional_weeks == 8: 
            return Decimal('0.015')
        elif additional_weeks == 16: 
            return Decimal('0.03')
        else:
            return Decimal('0')
        
    def calculate_profit(self):
        #Calculate sale proceeds with or without delay
        delay_bonus = self.calculate_delay_bonus()
        effective_buyer_rate = self.buyer_rate + delay_bonus
        sale_proceeds = self.face_value * effective_buyer_rate

        #calculate pepper cash value
        pepper_value = self.pepper_deal.calculate_pepper_value()

        # calculate various profit scenarios
        purchase_cost = self.face_value
        immediate_profit = sale_proceeds - purchase_cost

        #different redemption scenarios
        pepper_100 = immediate_profit + pepper_value
        pepper_915 = immediate_profit + (pepper_value * Decimal('0.915'))
        
        return { 
            'sale_proceeds': sale_proceeds, 
            'pepper_value': pepper_value, 
            'immediate_profit': immediate_profit, 
            'total_profit_100': pepper_100, 
            'total_profit_915': pepper_915, 
            'roi_100': (pepper_100 / purchase_cost * 100),
            'roi_915': (pepper_915 / purchase_cost * 100),
            'effective_buyer_rate': effective_buyer_rate * 100
        }
    
def create_streamlit_app():
    st.title("Gift Card Deal Analyzer")

    # ''' input section '''
    st.header("Enter deal details")

    col1, col2 = st.columns(2)

    with col1: 
        brand = st.text_input("Gift Card Brand", value="")
        face_value = st.number_input("Face Value ($)", min_value=0.0, max_value=1000.0, value=500.0, step=25.0)
        buyer_rate = st.number_input("Buyer Rate(%)", min_value=0.0, max_value=100.0, value=85.0, step=0.25) / 100
        payment_weeks = st.selectbox("Payment Delay (Weeks)", 
                                        options= [0, 2, 4, 8, 16], 
                                        format_func=lambda x: f"+{x} Weeks" if x != 0 else f"{x} Weeks (Standard 2 Weeks)" )
        
    with col2: 
        pepper_multiplier = st.number_input("Pepper Multiplier (X)", min_value=1, value=15, step=1)
        reg_rate = st.number_input("Regular Rate (X)", min_value=1, value=2, step=1)
        

    pepper_deal = PepperDeal(
        brand = brand, 
        face_value = face_value, 
        multiplier = pepper_multiplier, 
        reg_rate = reg_rate, 
        bonus_date = datetime.now() + timedelta(weeks = 2)
    )

    deal = Deal(
        face_value = Decimal(str(face_value)),
        buyer_rate = Decimal(str(buyer_rate)),
        pepper_deal = pepper_deal, 
        payment_delay_weeks = payment_weeks
    )

    if st.button("Calculate Profitability"):
        results = deal.calculate_profit()

        st.header("Deal Analysis")

        col1, col2, col3 = st.columns(3)

        with col1: 
            st.metric("Effective Buyer Rate", f"{results['effective_buyer_rate']:.2f}%")
            st.metric("Sale Proceeds", f"{results['sale_proceeds']:.2f}")

        with col2:
            st.metric("Pepper Value (100%)", f"${results['pepper_value']:.2f}")
            st.metric("Immediate Profit", f"${results['immediate_profit']:.2f}")
            
        with col3: 
            st.metric("Total ROI (100%)", f"{results['roi_100']:.2f}%")
            st.metric("Total ROI (91.5%)", f"{results['roi_915']:.2f}%")

        # ''' breakdown '''
        st.subheader("Breakdown")
        breakdown = pd.DataFrame({
            'Metric': [
                'Purchase Cost', 
                'Sale Proceeds', 
                'Pepper Value (100%)', 
                'Pepper Value (91.5%)',
                'Total Profit (100%)',
                'Total Profit (91.5%)'
            ], 
            'Amount': [
                f"{face_value:.2f}",
                f"{results['sale_proceeds']:.2f}",
                f"{results['pepper_value']:.2f}",
                f"{results['pepper_value'] * Decimal('0.915'):.2f}",
                f"${results['total_profit_100']:.2f}",
                f"${results['total_profit_915']:.2f}"
            ]
        })

        st.table(breakdown)

if __name__ == "__main__":
    create_streamlit_app()