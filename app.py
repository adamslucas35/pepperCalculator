import streamlit as st
import pandas as pd
import sqlite3

from datetime import datetime, timedelta, date
from decimal import Decimal
from pandas.tseries.holiday import USFederalHolidayCalendar


# pepper daily archive
# reading daily deal archive
df = pd.read_csv("Pepper Daily Deals Archive.csv")
# clean data from pepper daily deals archive
df['Brand'] = df['Brand'].astype(str)
df['Reg Rate'] = df['Reg Rate'].astype(str)
df['Brand'] = df['Brand'].str.replace('"', '')
df['Brand'] = df['Brand'].str.replace('JC Penney', 'JCPenney')
df['Brand'] = df['Brand'].str.replace('Bed, Bath, & Beyond', 'Bed Bath & Beyond')
df['Reg Rate'] = df['Reg Rate'].str.replace('X','')
df['Offer'] = df['Offer'].str.replace('X', '')
df[['Reg Rate', 'Offer']] = df[['Reg Rate', 'Offer']].apply(pd.to_numeric, errors='coerce')
unique_brands = sorted(df['Brand'].unique())



# ai buy rate clean data
df_ai = pd.read_csv('AI_BuyRate\PepperDeals_csv.csv')
df_ai['Date'] = pd.to_datetime(df_ai['Date']).dt.date
df_ai.sort_values('Date', ascending=False)
df_ai['Brand'] = df_ai['Brand'].astype(str)
df_ai['Brand'] = df_ai['Brand'].str.replace('.com','')
date_cutoff = date.today() - timedelta(2)
current_brands = sorted(df_ai['Brand'].unique())
active_buy_rates= df_ai['Brand'].groupby(df_ai['BuyRate'])

# date setup
today = date.today()
holidays = pd.DatetimeIndex(USFederalHolidayCalendar().holidays())
holiday_dates = holidays.to_pydatetime()
# set up pepper valuation
class PepperDeal: 
    def __init__(self, brand, face_value, quantity, multiplier, reg_rate, bonus_date, redemption_rate):
        self.brand = brand
        self.face_value = face_value
        self.quantity = quantity
        self.multiplier = multiplier
        self.reg_rate = reg_rate
        self.bonus_date = bonus_date
        self.base_coins_per_dollar = 20
        self.coins_per_dollar_redemption = 2000
        self.redemption_rate = redemption_rate

    def calculate_pepper_value(self):
        # ''' Calculate value of pepper coins'''
        total_coins = (
            self.face_value * (self.base_coins_per_dollar * self.multiplier)
        )
        instant_coins = self.reg_rate * self.base_coins_per_dollar * self.face_value


        return { 
            'cash_value': Decimal(total_coins) / self.coins_per_dollar_redemption, 
            'instant_coins': instant_coins,
            'future_coins': (self.multiplier * self.base_coins_per_dollar * self.face_value) - instant_coins,
            'future_payout_date': self.bonus_date,
            'redemption_rate': self.redemption_rate
        }

        
# set up AI valuation
class Deal:
    def __init__(self, 
                 face_value: Decimal,
                 quantity: int,
                 buyer_rate: Decimal, 
                 pepper_deal: PepperDeal, 
                 payment_delay_weeks: int, 
                 brand: str = None):
        self.face_value = face_value
        self.quantity = quantity
        self.buyer_rate = buyer_rate
        self.pepper_deal = pepper_deal
        self.payment_delay_weeks = payment_delay_weeks
        self.brand = brand

    def calculate_delay_bonus(self): 
        #Calculate bonus rate on payment delays
        # NOTE: percentage of buyer_rate (not an addition!)
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
        effective_buyer_rate = self.buyer_rate * (1 + delay_bonus) # see note in def calculate_delay_bonus()
        sale_proceeds = self.face_value * effective_buyer_rate * self.quantity

        days_until_sunday = (6 - today.weekday()) % 7
        next_sunday = today + timedelta(days=days_until_sunday)
        deposit_date = next_sunday + timedelta(days=4) # two thursdays from Sunday
        payout_week = deposit_date.isocalendar()[1]

        if any(holiday.isocalendar()[1] == payout_week and 
               holiday.isocalendar()[2] <= 4
               for holiday in holiday_dates):
            deposit_date += timedelta(days=1)

        deposit_date = deposit_date + timedelta(weeks=self.payment_delay_weeks)

        

        #calculate pepper cash value
        pepper_values = self.pepper_deal.calculate_pepper_value()

        # calculate various profit scenarios
        purchase_cost = self.face_value * self.quantity
        cash_profit = sale_proceeds - purchase_cost
        

        #different redemption scenarios
        pepper_cash_value = pepper_values['cash_value']


        # TODO: Maybe choose scenario? Show optoins of pepper redemption. 
        pepper_100 = cash_profit + pepper_cash_value
        pepper_915 = cash_profit + (pepper_cash_value * Decimal('0.915'))
        pepper_redemption = cash_profit + (pepper_cash_value * Decimal(pepper_values['redemption_rate'])) 



        return { 
            'test': "TEST",
            'sale_proceeds': sale_proceeds, 
            'cash_profit': cash_profit, 
            'deposit_date': deposit_date,
            'total_profit_100': pepper_100, 
            'total_profit_915': pepper_915, 
            'roi_100': (pepper_100 / purchase_cost * 100) ,
            'roi_915': (pepper_915 / purchase_cost * 100),
            'effective_buyer_rate': effective_buyer_rate * 100, 
            'pepper_value': pepper_values['cash_value'], 
            'total_pepper_coins': pepper_values['instant_coins'] + pepper_values['future_coins'],
            'instant_pepper_coins': pepper_values['instant_coins'],
            'future_pepper_coins': pepper_values['future_coins'],
            'future_payout_pepper_coins': pepper_values['future_payout_date'],
            'at_whole_date': max(deposit_date, pepper_values['future_payout_date']), 
            'pepper_redemption': pepper_redemption,
            'paper_pl':  sale_proceeds + pepper_redemption
        }

    
def create_streamlit_app():
    st.title("Gift Card Deal Analyzer")

    # ''' input section '''
    st.header("Enter deal details")

    col1, col2 = st.columns(2)

    with col1: 
        
    
        available_combos = df_ai.groupby(['Brand','Denom'])['BuyRate'].mean()
        ai_acquiCost = df_ai.groupby(['Brand'])['AcquiCost'].mean()


        live = st.checkbox("Live", value=True)
        
        if live : 
            list_brands = current_brands
        else:
            list_brands = unique_brands
        
        brand = st.selectbox("Gift Card Brand", options=list_brands, placeholder="Choose a brand...")
        
        available_denoms = sorted(df_ai[
            (df_ai['Brand'] == brand) &
            (df_ai['Date'] >= date_cutoff)
            ]['Denom'].unique())
        
        if live:
            face_value = st.selectbox("Select Denomination", 
                                      options=available_denoms,
                                      placeholder="Choose denom")
        else:
            face_value = st.number_input("Face Value ($)", min_value=0.0, max_value=1500.0, value=500.0, step=25.0)

        quantity = st.number_input("Quantity", min_value=1)


        if live:
            buyer_rate = st.number_input("Buyer Rate(%)", value=available_combos[(brand, face_value)], disabled=True)
        else: 
            buyer_rate = st.number_input("Buyer Rate(%)", min_value=0.0, max_value=100.0, value=100.0, step=0.25)
        
        
        payment_weeks = st.selectbox("Payment Delay (Weeks)", 
                                        options= [0, 2, 4, 8, 16], 
                                        format_func=lambda x: f"+{x} Weeks" if x != 0 else f"{x} Weeks (Standard 2 Weeks)" )
        
        
    with col2: 
        if live:
            pepper_multiplier = st.number_input("Pepper Multiplier (X)", min_value=1, value= 100 - int(ai_acquiCost[(brand)]), step=1)
        else:
            pepper_multiplier = st.number_input("Pepper Multiplier (X)", min_value=1, value= 20, step=1)
        brand_data = df[df['Brand'] == brand]
        historical_max_rate = brand_data['Offer'].max()
        st.text(f"Historical max pepper rate: {historical_max_rate}X.")
        default_reg = brand_data['Reg Rate'].max()
        reg_rate = st.number_input("Regular Rate (X)", min_value=1, value=int(default_reg), step=1)
        
        redemption = st.number_input("Expected Redemption Rate", min_value=0.25, value=100.00, step=0.25)

    pepper_deal = PepperDeal(
        brand = brand, 
        face_value = face_value, 
        quantity = quantity,
        multiplier = pepper_multiplier, 
        reg_rate = reg_rate, 
        bonus_date = date.today() + timedelta(weeks = 2) if pepper_multiplier != reg_rate else date.today(),
        redemption_rate = redemption
    )

    deal = Deal(
        face_value = Decimal(str(face_value)),
        quantity = Decimal(str(quantity)),
        buyer_rate = Decimal(str(buyer_rate / 100)),
        pepper_deal = pepper_deal, 
        payment_delay_weeks = payment_weeks,
    )

    

    if st.button("Calculate Profitability"):
        results = deal.calculate_profit() 

        st.header("Deal Analysis")

        col1, col2, col3 = st.columns(3)

        total_value = face_value * quantity
        instant_cash = float(results['sale_proceeds']) - total_value
        with col1: 
            
            st.metric("Total Cash Value Spent", f"${total_value:.2f}")
            st.metric("Buyer Rate", f"{results['effective_buyer_rate']:.2f}%")
            st.metric("Sale Proceeds", f"${results['sale_proceeds']:.2f}")
            st.metric("Instant Cash P/L", f"${instant_cash:.2f}")
            st.metric("Deposit Date", f"{results['deposit_date']}")
        with col2:
            st.metric("Total Pepper Coins Earned", f"{int(results['total_pepper_coins']):,d}")
            st.metric("Instant Pepper Coins", f"{int(results['instant_pepper_coins']):,d}")
            st.metric("Future Pepper Coins", f"{int(results['future_pepper_coins']):,d}")
            st.metric(f"Pepper Coins at {redemption:.2f}% value", f"${results['pepper_redemption'] / 100:.2f}")
            st.metric("Future Pepper Coins Payout Date", f"{results['future_payout_pepper_coins']}")

        

        with col3: 
            st.metric("Pepper Coins Cash Value", f"${results['pepper_value']:.2f}")
            st.metric("filler","filler")
            st.metric("filler","filler")
            st.metric("Paper P/L", f"${instant_cash + float(results['pepper_redemption'] / 100):.2f}") 
            st.metric("At Whole Date", f"{results['at_whole_date']}")

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
                f"{face_value * quantity:.2f}",
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