import copy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import random
import ui.ciiModel as cii
import matplotlib.colors as mcolors
import os
import tempfile



"""
Days in dd to apply 

charter rate = 25000

surface prep cost /square m

washing cost / square m 

applicaiton cost / square m

offire cost for cleaning






1. Surface preperation cost  (square meter * surface prep cost)

2. Washing cost (square meter)

3. Paint Application Cost (SQUARE M)

4. Offhire Cost (charter rate * days in yard)

5. Shipyard Rent (days in yard)

6. offhire cost for cleaning


"""



class tco_model:

    def __init__(self, coating_type="XGIT-Fuel", cleaning_frequency=None, average_power=4000, fuel_type="VLSFO",
                 vessel_efficiency=0.7, fixed_cleanings=None, debug=False, region="equatorial",
                 fouling_type="calcareous", growth_type="gaussian", reactive_cleaning=None, activity_rate=0.5,
                 max_speed=20,imo_from_clarksons = None,cleaning_subscription = None,coated_sqm = 800,charter_rate = 25000,
                 offhire_cost_per_cleaning = 10000,m_modifier = 1,dwt = 53000, vessel_type = "Container Ship",distance = 312542):
        self.average_power = average_power
        self.coating_type = coating_type
        self.cleaning_frequency = cleaning_frequency  # in months
        self.debug = debug
        self.cleaning_frequency = cleaning_frequency
        self.average_power = average_power  # average power output in kW
        self.vessel_efficiency = vessel_efficiency  # efficiency to be used in fuel/energy calculations
        self.activity_rate = 0.4  # % of the day the vessel is using power
        self.fuel_type = fuel_type
        self.cleaning_events = fixed_cleanings
        self.region = region
        self.fouling_type = fouling_type
        self.growth_type = growth_type
        self.reactive_cleaning = reactive_cleaning
        self.imo_from_clarksons = imo_from_clarksons

        self.cleaning_subscription = cleaning_subscription

        self.max_speed = max_speed
        self.activity_rate = activity_rate
        self.imo = imo_from_clarksons

        self.charter_rate = charter_rate
        self.offhire_cost_per_cleaning = offhire_cost_per_cleaning
        self.coated_sqm = coated_sqm
        
        self.sfoc_clarksons = None

        #details for cii calc
        self.dwt = dwt
        self.vessel_type = vessel_type
        self.distance = distance



        self.vessel_name = f"Simulated {average_power}kW Vessel"
        

        self.num_cleanings = 0

        default_reactive_cleaning = 10

        if self.imo_from_clarksons is not None:
            # we are loading vessel data from clarksons for this simulation
            # from clarksons we are loading the speed, the power, and vessel efficiency, sfoc, fuel consumption
            
            if self.debug:
                print(f"Loading data for IMO {self.imo_from_clarksons} from clarksons")
            
            clarksons_path = r"D:\clarksies\Cleaned Clarksons Master.csv"
            
            clakrsons_data = pd.read_csv(clarksons_path)

            

            #try to find the imo number from the IMO Number column, if it doesnt exist warn the user and leave the conditional
            try:
                self.vessel_data = clakrsons_data.loc[clakrsons_data['IMO'] == self.imo]
            except:
                self.vessel_data = None
                print(f"IMO number {self.imo} not found in the clarksons data")
                
            #if the vessel data is found, then we can load the data
            if self.vessel_data is not None:
                #load the name of the vessel from the Name column
                self.vessel_name = self.vessel_data['Name'].values[0]

                if self.debug:
                    print(f"Vessel name from clarksons is {self.vessel_name}")



                #sfoc: Main Engine Model SFOC (g/kWh)
                #total energy created : Engine Derived Total Mechanical Generated (kW)
                #total propulsion power : Engine Derived Total Mechanical Propulsion (kW)
                #speed : Speed (knots)
                #fuel type : Main Engine Fuel Type

                #calcualte the vessel efficiency from the total energy created and the total propulsion power
                total_engine_power = self.vessel_data['Engine Derived Total Mechanical Generated (kW)'].values[0]
                total_propulsion_power = self.vessel_data['Engine Derived Total Mechanical Propulsion (kW)'].values[0]
                self.vessel_efficiency = round(total_propulsion_power / total_engine_power,2)

                self.average_power = total_engine_power

                #load the speed of the vessel
                self.max_speed = self.vessel_data['Speed (knots)'].values[0]

                if self.dwt is None:
                    if self.debug:
                        print("DWT not provided, loading DWT from clarksons data")
                    
                    self.dwt = self.vessel_data['DWT'].values[0]

                    if self.debug:
                        print(f"DWT from clarksons is {self.dwt}")


                #load the fuel type of the vessel
                self.sfoc_clarksons = self.vessel_data['Main Engine Model SFOC (g/kWh)'].values[0]

        #check to see if the sfoc is None, if it is then we will use a default value
        if self.sfoc_clarksons is None:
            self.sfoc = 190
        else:
            self.sfoc = self.sfoc_clarksons






        self.load_coating_details(coating_type)


            #load in the clarksons data

        self.load_fuel_details(fuel_type)

        # check to make sure the user only provided one of the cleaning types
        if cleaning_frequency is not None and fixed_cleanings is not None:
            print("Both cleaning frequency and fixed cleanings were provided. Defaulting to reactive cleaning at 10%.")
            self.reactive_cleaning = default_reactive_cleaning
            self.cleaning_type = "Reactive Cleaning"
            breakpoint()
        
        if cleaning_frequency is not None and reactive_cleaning is not None:
            print(
                "Both cleaning frequency and reactive cleanings were provided. Defaulting to reactive cleaning at 10%.")
            self.reactive_cleaning = default_reactive_cleaning
            self.cleaning_type = "Reactive Cleaning"
            breakpoint()

        if fixed_cleanings is not None and reactive_cleaning is not None:
            print("Both fixed cleanings and reactive cleanings were provided. Defaulting to reactive cleaning at 10%.")
            self.reactive_cleaning = default_reactive_cleaning
            self.cleaning_type = "Reactive Cleaning"
            breakpoint()

        

        if cleaning_frequency is not None:
            self.cleaning_type = "Periodic Cleanings"
        elif fixed_cleanings is not None:
            self.cleaning_type = "Fixed Cleanings"
        elif reactive_cleaning is not None:
            self.cleaning_type = "Reactive Cleanings"

        print(f"This is the coating type {self.coating_type}")

        self.model_name = self.coating_type + "\n" + self.cleaning_type

        # fixed cleanings are a list of day numbers that represents when the vessel is to be cleaned within the 5 year period
        if self.cleaning_type == "Fixed Cleanings":
            self.cleaning_events = fixed_cleanings
            self.cleaning_frequency = "Days : "
            for cleaning in fixed_cleanings:
                self.cleaning_frequency += " " + str(cleaning) + ", "
            self.cleaning_frequency = self.cleaning_frequency[:-2]
            print(f"Cleaning events are as follows: {self.cleaning_frequency}")

        if self.debug:
            print(f"FINISHED ASSEMBLING MODEL FOR {coating_type}")
            print(f"Coating type is {coating_type}")
            print(f"Cleaning frequency is {cleaning_frequency}")
            print(f"Average power is {average_power}")

        fouling_type = self.fouling_type.lower()
        region = self.region.lower()

        if region == "equatorial":
            if fouling_type == "slime":
                self.t = 87
                self.m = 37.08
            elif fouling_type == "non-shell":
                self.t = 271.4
                #self.m = 73.11
                self.m = 300
            elif fouling_type == "calcareous":
                self.t = 379.4
                self.m = 187.2

        elif region == "mediterranean":
            if fouling_type == "slime":
                self.t = 271.9
                self.m = 99.31129
            elif fouling_type == "non-shell":
                self.t = 385.5
                self.m = 124.4
            elif fouling_type == "calcareous":
                self.t = 726.4
                self.m = 129.7
        else:
            print("Region not found")
            return None
        
        self.m = self.m * m_modifier

        self.shipyard_cost = 0

        self.t_modifier = ((((self.max_speed - 10)/100) + 1) * 1/(1-activity_rate)) * self.self_cleaning

        self.g = self.biofouling_delay* self.t_modifier


        #calculate the self cleaning delay from the max speed and the activity rate, this value will be used to multiply the t value
        self.new_t = 0.5 * (np.sqrt(self.g**2 * self.t**2 + 2*self.m**2) + self.g* self.t)


        #20-10/100 = 0.1
        #0.1 + 1 = 1.1

        #1/(0.2-1) =  
        print(f"t modifier is {self.t_modifier}")

        """
        rolands github schwartau-extra
        """

        """
        modification based off of m value

        self cleaning

        """

    def load_fuel_details(self, fuel_type):
        # load the table of fuel details
        self.fuel_details = pd.read_csv(r"C:\Dashboard\tco_ui\tco_ui\tco\fuel_prices_today.csv")

        # Global 20 Ports Average	VLSFO	663.5

        # in g/kWh
        self.SFOC_values = {
            "VLSFO": 205,
            "MGO": 195,
            "IFO380": 210
        }
        # values above and below are for sanity

        # in MJ/kg
        self.CALORIFIC_VALUES = {
            "VLSFO": 40.5,
            "MGO": 42.7,
            "IFO380": 40.1
        }

        """#in kWh/t #from calorific values
        self.kWh_per_t = {
            "VLSFO": 11250.01,
            "MGO": 11861.12,
            "IFO380" : 11138.90
        }"""


        #kWh per t is 1 000 000 / sfoc
        self.kWh_per_t = {
            "VLSFO": 4878.04878,
            "MGO": 5128.20513,
            "IFO380": 4761.90476
        }

        # price in USD/t
        # Correct approach to filter the DataFrame
        self.fuel_cost = self.fuel_details.loc[
            (self.fuel_details['Fuel Type'] == fuel_type) &
            (self.fuel_details['Location'] == 'Global 20 Ports Average')
            ]['Price $/mt'].values[0]  # Assuming you want to extract the 'Cost' value

        # energy density in kWh/t
        # real energy density = base density * 0.7 (for 70% efficiency)
        # if a vessel is burning fuel which has 10,000kWh of energy per ton, a vessel with 70% efficiency will only be able to get 7,000kWh of that energy
        if self.imo_from_clarksons is None:
            self.energy_density = self.kWh_per_t[fuel_type] * self.vessel_efficiency
            self.sfoc = self.SFOC_values[fuel_type]
        else:
            self.energy_density = (1000000/self.sfoc) * self.vessel_efficiency

        if self.debug:
            print(f"Details for {fuel_type} are as follows:")
            print(f"Fuel cost is {self.fuel_cost}$USD/t")
            print(f"Energy density is {self.energy_density}kWh/t")

    def load_coating_details(self, coating_type):

        # coating	out of dock savings	Speed Loss (%)	power loss 5y	increase from cleaning

        #print the current directory
        import os
        print(f"current directory is {os.getcwd()}")

        # load the table of coating details
        self.coating_details = pd.read_excel(r'C:\Dashboard\tco_ui\tco_ui\tco\coating_details 1.xlsx', skiprows=5)

        if self.debug:
            print(f"Coating details are as follows:")
            print(self.coating_details)

        self.this_coating = self.coating_details.loc[self.coating_details['coating'] == coating_type]

        if self.debug:
            print(f"Details for {coating_type} are as follows:")
            print(self.this_coating)

        # out_of_dock_savings	Speed Loss (% over 5 years)	power loss (%over 5y)	% increase from cleaning	cleaning result

        self.out_of_dock_savings = \
            self.coating_details.loc[self.coating_details['coating'] == coating_type, 'out_of_dock_savings'].values[0]
        
    
        
        #self.daily_power_loss = self.power_loss / (365 * 5) # real line
       
        
        
        self.power_increase_at_max_biofouling = self.coating_details.loc[
            self.coating_details['coating'] == coating_type, 'power_increase_at_max_biofouling'].values[0]

        # a value that represents the degradation of the coating from cleaning. The value is represented as a % of the power loss. Each time
        # a cleaning is performed, the vessel will go back to the cleaning result value and then the degradation will be applied to the power loss
        self.cleaning_cost = \
            self.coating_details.loc[self.coating_details['coating'] == coating_type, 'cleaning cost'].values[0]

        self.coating_cost = \
            self.coating_details.loc[self.coating_details['coating'] == coating_type, 'coating cost'].values[0]

        # starting_coating_thickness	cleaning_thickness_impact	thickness_loss_yearly, initial_roughness
        self.starting_coating_thickness = \
            self.coating_details.loc[
                self.coating_details['coating'] == coating_type, 'starting_coating_thickness'].values[
                0]
        self.cleaning_thickness_impact = \
            self.coating_details.loc[
                self.coating_details['coating'] == coating_type, 'cleaning_thickness_impact'].values[0]
        self.thickness_loss_yearly = \
            self.coating_details.loc[self.coating_details['coating'] == coating_type, 'thickness_loss_yearly'].values[0]
        self.thickness_loss_daily = self.thickness_loss_yearly / 365
        self.initial_roughness = \
            self.coating_details.loc[self.coating_details['coating'] == coating_type, 'initial_roughness'].values[0]

        self.biofouling_delay = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'growth_delay_vs_SPC'].values[0]
        self.biofouling_delay = float(self.biofouling_delay)

        self.self_cleaning = float(self.coating_details.loc[self.coating_details['coating'] == coating_type, 'self_cleaning_10kn'].values[0])


        #biocide vars
        #initial_biocide_level	biocide_leaching_rate_yearly	biocide_removed_from_cleaning	biocide_efficacy


        self.initial_biocide_level = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'initial_biocide_level'].values[0]
        self.biocide_leaching_rate_yearly = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'biocide_leaching_rate_yearly'].values[0]
        self.biocide_leaching_rate_daily = self.biocide_leaching_rate_yearly / 365
        self.biocide_removed_from_cleaning = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'biocide_removed_from_cleaning'].values[0]
        self.biocide_efficacy = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'biocide_efficacy'].values[0]



        #load the UWH area, and coating price from clarksons if the user has provided an imo number
        #check to see if we have a self.vessel_data attribute exists in the class
        

        if hasattr(self, 'vessel_data') and self.vessel_data is not None:
        
        
            
            self.coated_sqm = self.vessel_data['Average Wetted Surface Area'].values[0]


            if coating_type == "XGIT-Fuel":
                self.coating_cost = self.vessel_data['XGIT Fuel Revenue ($)'].values[0]

                print(f"using xgit fuel, the coating cost is {self.coating_cost}")
                #breakpoint()
            elif coating_type == "SPC":
                self.coating_cost = self.vessel_data['S1 - Antifouling Hull Coating ($)'].values[0]
            elif coating_type == "Silicone":
                self.coating_cost = self.vessel_data['S3 - Antifouling Hull Coating ($)'].values[0]




            


        #load in shipyard costs 

        self.application_length_days = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'application_length_days'].values[0]

        self.surface_prep_sqm = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'surface_prep_sqm'].values[0]

        self.washing_sqm = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'washing_sqm'].values[0]

        self.application_sqm = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'application_sqm'].values[0]

        self.shipyard_rent = self.coating_details.loc[self.coating_details['coating'] == coating_type, 'shipyard_rent'].values[0]


        #calcualte shipyard costs for this sim

        self.application_offhire_cost = self.application_length_days * self.charter_rate

        self.surface_prep_cost = self.surface_prep_sqm * self.coated_sqm

        self.washing_cost = self.washing_sqm * self.coated_sqm

        self.application_cost = self.application_sqm * self.coated_sqm

        self.shipyard_rent_cost = self.shipyard_rent * self.application_length_days



        self.total_shipyard_cost = self.surface_prep_cost + self.washing_cost + self.application_cost + self.application_offhire_cost + self.shipyard_rent_cost

        #round all the values to 2 decimal places
        self.total_shipyard_cost = round(self.total_shipyard_cost,2)
        self.surface_prep_cost = round(self.surface_prep_cost,2)
        self.washing_cost = round(self.washing_cost,2)
        self.application_cost = round(self.application_cost,2)
        self.application_offhire_cost = round(self.application_offhire_cost,2)
        self.shipyard_rent_cost = round(self.shipyard_rent_cost,2)

        self.coated_sqm = round(self.coated_sqm,2)
        self.coating_cost = round(self.coating_cost,2)



        







        """
        1. Surface preperation cost  (square meter * surface prep cost)

        2. Washing cost (square meter)

        3. Paint Application Cost (SQUARE M)

        4. Offhire Cost (charter rate * days in yard)

        5. Shipyard Rent (days in yard)

        6. offhire cost for cleaning

        
        
        Days in dd to apply 

        charter rate = 25000

        surface prep cost /square m

        washing cost / square m 

        applicaiton cost / square m

        offire cost for cleaning"""

    def get_cost_assumptions(self):
        """
        Returns all of the cost assumptions as a dict"""

        assumptions = {
            "surface_prep_rate": "$" + str(self.surface_prep_sqm) + "/sqm",
            "surface_prep_cost": "$" + str(self.surface_prep_cost),
            "washing_rate": "$" + str(self.washing_sqm) + "/sqm",
            "washing_cost": "$" + str(self.washing_cost),
            "application_rate": "$" + str(round(self.application_sqm,2)) + "/sqm",
            "application_cost": "$" + str(self.application_cost),
            "application_length_days": str(self.application_length_days) + " days",
            "application_offhire_rate": "$" + str(self.charter_rate),
            "application_offhire_cost": "$" + str(self.application_offhire_cost),
            "total_shipyard_cost": "$" + str(self.total_shipyard_cost),
            "yard_rent": "$" + str(self.shipyard_rent_cost),
            "fuel_cost": "$" + str(self.fuel_cost),
            "fuel_type": self.fuel_type,
        }


        return assumptions
    # Define the logistic function
    def logistic_growth(self, x, growth_rate, limit=40):

        # reasoning: the midppint of the sigmoiod function is the higest biofouling pressure
        midpoint = (5 * 365) / 2

        result = limit / (1 + np.exp(-growth_rate * (x - midpoint)))
        if self.debug:
            print(f"Logistic growth result is {result}")
        return result

    def gaussian_growth(self, x, max_value=100):
        """
        t is the time to reach the max
        max_growth is the level of max growth that can happen
        m is how quickly we get to the maximum growth


        :param x:
        :param max_growth:
        :param half_width:
        :param limit:
        :return:
        """

        
        #heres how we can fix the max not being 100
        #1. calculate the max value of the gaussian function
        #2. divide the current value by the max value to get the percentage of the max value
        #3. multiply the max value by the percentage to get the current value
        #g = self.biofouling_delay* self.t_modifier

        #x_value_of_max = 0.5 * (np.sqrt(g**2 * self.t**2 + 2*self.m**2) + g* self.t)

        max_y_modifier = max_value * ((self.new_t / (self.t * self.g) )* np.exp(-(((self.new_t - (self.t * self.g)) / (self.m)) ** 2)))


        if max_y_modifier == 0:
            print(f"np term is {np.exp(-((self.new_t - ((self.t * self.g)) / (self.m)) ** 2))}")

            print(f"the term in the exponent is {-(((self.new_t - (self.t * self.g)) / (self.m)) ** 2)}")

            #print all the terms in the np term
            print(f"new t is {self.new_t}")
            print(f"t is {self.t}")
            print(f"g is {self.g}")
            print(f"m is {self.m}")
            print(f"max value is {max_value}")

            #print out the np term with all the values as an equation
            
            

            print(f"max y modifier is {max_y_modifier}")


        # result = max_value *  np.exp(-((x-self.t) / self.m) ** 2)
        #result = max_value * (x / self.t) * np.exp(-((x - self.t) / self.m) ** 2) #no biofouling delay
        #result = (max_value * (x / ((self.t * self.biofouling_delay)* self.t_modifier)) * np.exp(-((x - ((self.t * self.biofouling_delay)* self.t_modifier)) / (self.m * self.biofouling_delay)) ** 2)) no sub for g
        #result = (max_value * (x / (self.t * self.biofouling_delay* self.t_modifier)) * np.exp(-((x - (self.t * self.biofouling_delay* self.t_modifier)) / (self.m)) ** 2)) #no sub for g
        #result = (max_value * (x / ((self.t * self.biofouling_delay)* self.t_modifier)) * np.exp(-((x - ((self.t * self.biofouling_delay)* self.t_modifier)) / (self.m * self.biofouling_delay)) ** 2)) #no sub for g
        #result = (max_value * (x / (self.t * self.g)) * np.exp(-((x - (self.t * self.g)) / (self.m)) ** 2)) # sub for g

        result = max_value * ((max_value * (x / (self.t * self.g)) * np.exp(-((x - (self.t * self.g)) / (self.m)) ** 2)) / max_y_modifier) # normalize for 100 max value







        if self.debug:
            print(
                f"Calculating gaussian growth for day {x} with t = {self.t}, max_value = {max_value}, m = {self.m}\nResult is {result}")
        return result

    def calculate_total_energy_used(self, daily_average_power_outputs):
        # Calculate the number of active hours per day
        #We dont need to use the vessel activity here because it is now taken into consideration in the power output calculation via self cleaning
        
        # Calculate daily energy usage for each day and sum up for total energy used
        total_energy_used_kwh = sum(power * 24 for power in daily_average_power_outputs)

        return total_energy_used_kwh

    def run_5y(self):
        """
        Runs a simulation that outlines a vessels power loss over 5 years based off of the parameters set in the init.

        Power % change is on the y axis and time is on the x axis

        The vessel will start with a negative percent change (from the out of dock savings) and then will increase over time.

        The % change will be defined from the result of a sigmoid function with the parameters set in the init.

        Every self.cleaning_frequency months, the vessel will be "cleaned" which will decrease the % power change. The % change will be estimated by
        calculating a % change from the self.increase_from_cleaning parameter.

        The model will create a dataframe a value for every day in the 5 year period.

        Assumes the coating thickness will decrease over time and during each cleaning. Reduced thickness will result in a higher roughness which will increase the power loss

        Assuming 20micron roughness increase is 1% power loss

        The dataframe will incude the following columns:
        - date
        - power_change
        - power_output

        :return:
        - the final df
        """
        """if self.cleaning_events is not None:
            #divide the days in the list by 365 to get the year
            cleaning_years = [round(x / 365,2) for x in self.cleaning_events]
            print(f"Applying cleanings at fixed times (in yrs) : {cleaning_years}")"""
        


        if self.cleaning_events is None:
            self.cleaning_events = []

        start_date = pd.to_datetime('2020-01-01')

        # Initialize the simulation parameters
        days_in_5_years = int(365 * 5)
        self.days_in_sim = days_in_5_years
        dates = pd.date_range(start=start_date, periods=days_in_5_years, freq='D')
        power_changes = np.zeros(days_in_5_years)
        power_output = np.zeros(days_in_5_years)

        coating_thickness = np.zeros(days_in_5_years)
        coating_roughness = np.zeros(days_in_5_years)

        biocide_levels = np.zeros(days_in_5_years)

        coating_thickness_daily_loss = []

        biofouling_growth_level = np.zeros(days_in_5_years)

        calcareous_growth_level = np.zeros(days_in_5_years)
        slime_growth_level = np.zeros(days_in_5_years)
        non_shell_growth_level = np.zeros(days_in_5_years)

        speeds = generate_speeds(self.activity_rate, self.max_speed, days_in_5_years)

        average_speed = np.mean(speeds)

        growth_level = 0

        #the average speed of the vessel is the speed at which it is using the average power


        # Set initial power change due to out of dock savings
        power_changes[0] = -self.out_of_dock_savings * 100
        power_output[0] = self.average_power * (1 - self.out_of_dock_savings)
        coating_thickness[0] = self.starting_coating_thickness
        coating_roughness[0] = self.initial_roughness
        biocide_levels[0] = self.initial_biocide_level

        self.power_out_of_dock = power_output[0]  # the power in kW that the vessel will start with

        if self.debug:
            print(f"The power change for the first day is {power_changes[0]}")
            print(f"The power output for the first day is {power_output[0]}")

        if self.debug:
            if self.cleaning_frequency == 0:
                print("No cleaning will be applied")

        self.last_cleaning = 0

        coating_thickness_daily_loss.append(0)

        for day in range(1, days_in_5_years):
            # Simulate gradual power loss over time
            if self.debug:
                print(f"Day {day}")
                #print(f"Daily power loss is {self.daily_power_loss}")

            # apply thickness reduction
            coating_loss_today = 0
            roughness_increase_today = 0

            coating_loss_from_cleaning = 0
            roughness_increase_from_cleaning = 0
                
            #print(f"(Non-Cleaning) Thickness yesterday was {coating_thickness[day-1]}")
            #print(f"(Non-Cleaning) Thickness being reduced by {self.thickness_loss_daily}")
            coating_loss_today += self.thickness_loss_daily
            roughness_increase_today += (self.thickness_loss_daily * 0.5)
            #print(f"(Non-Cleaning) Thickness is now {coating_thickness[day]}")

            biocide_released_today = self.biocide_leaching_rate_daily
            
            
            # roughness increase is based off of the thickness loss per day, roughness increases at 50% of the rate of the daily thickness loss
            # power_change_today = power_changes[day - 1] + (self.daily_power_loss)

            power_change_today = 0
            power_reduction_cleaning = 0

            if self.growth_type == "sigmoid":
                logistic_result_yesterday = self.logistic_growth(day - 1, self.daily_power_loss, 40)
                logistic_result_today = self.logistic_growth(day, self.daily_power_loss, 40)

                logistic_result = logistic_result_today - logistic_result_yesterday

                if self.debug:
                    print(f"Logistic result is {logistic_result}")

                power_change_today = power_changes[day - 1] + logistic_result
                growth_level = power_change_today


                if self.debug:
                    print(f"Power change today is {power_change_today}")

                power_changes[day] = power_change_today

            elif self.growth_type == "linear":
                growth_power_increase = power_changes[day - 1] + self.daily_power_loss
                growth_level = growth_power_increase

                power_change_today += growth_power_increase

            elif self.growth_type == "gaussian":

                if self.last_cleaning is None:
                    days_since_cleaning = day
                else:
                    days_since_cleaning = day - self.last_cleaning

                # assuming this will output a value between 0 and 100. 0 representing no biofouling and 100 representing the maximum biofouling

                #print the content ant types of self.t and self.biofouling delay


                #old calculation for new t ((self.t * self.biofouling_delay)* self.t_modifier)
                if days_since_cleaning > self.new_t:
                    # if we are past the number of days it takes to reach the max value, then we will just use the max value. we need to do this because the gaussian function will start to decrease after the max value
                    
                    gaussian_growth_level = 1 #wrong line (uncoment if you want)

                    #above code is wrong ^ gpt would have never got this i am still better than ai
                    #explination why we need below : the max level of biofouling isnt 1, because we modified the guassian function to force
                    #it through the origin, with the (x/t) term, and probably other things like biofouling delay withinin the guassian method. because of this
                    #we need to explicitly calculate the value.

                    max_level = self.gaussian_growth(x=self.new_t)
                    gaussian_growth_level = max_level

                else:
                    # otherwise, we will use the gaussian function to calculate the growth level
                    gaussian_growth_level = self.gaussian_growth(x=days_since_cleaning)




                growth_level = gaussian_growth_level


                # power_change_today = power_changes[day - 1] + (self.power_increase_at_max_biofouling * (gaussian_growth_level/100))
                # power_change_today = (-self.out_of_dock_savings * 100) + (1-self.power_reduction_from_cleaning) + (self.power_increase_at_max_biofouling * gaussian_growth_level)
                growth_power_increase = (-self.out_of_dock_savings * 100) + (
                        self.power_increase_at_max_biofouling * gaussian_growth_level) 

                # power_change_today = power_changes[day - 1] + gaussian_growth_level

                """if power_change_today > (self.power_increase_at_max_biofouling*100):
                    power_change_today = (self.power_increase_at_max_biofouling*100)"""

                power_change_today += growth_power_increase

                """
                Heres how the above code works:
                - We calculate the days since the last cleaning
                - We use the gaussian function to calculate the growth level (0-100)
                - Gaussian growth decays after the max value is reached, so we check to see if we are past the max value and if so we just use the max value
                - We then apply the growth level to the daily power loss
                - We then add the result to the power changes array
                """

            if self.debug:
                print(f"This is the reaction cleaning {self.reactive_cleaning}")

            # calculate what the roughness today would be 
            #roughness_increase_from_cleaning = ((self.cleaning_thickness_impact * 0.5)* float((growth_level/100)))


            # this has to happen after the cleaning impacts the thickness and roughness
            roughness_power_increase = (((coating_roughness[day-1] + roughness_increase_today) - self.initial_roughness) / 20)

            # list of fixed cleaning events
            if self.cleaning_type == "Fixed Cleanings":
                if day in self.cleaning_events:  # check to see if the current day is a cleaning day
                    # Apply improvement from cleaning
                    
                    if self.debug:
                        print(f"Fixed Cleaning applied on day {day}")
                    #if (1 + power_changes[day] / 100) * self.average_power > self.power_out_of_dock: #haha, this makes it so that we dont apply a cleaning if we are at 
                    power_reduction_cleaning = (-self.out_of_dock_savings * 100) 
                    power_change_today = power_reduction_cleaning

                    coating_loss_from_cleaning = (self.cleaning_thickness_impact * float(growth_level/100))
                    roughness_increase_from_cleaning = ((self.cleaning_thickness_impact * 0.5)* float((growth_level/100)))
                    biocide_loss_from_cleaning = self.biocide_removed_from_cleaning * float((growth_level/100))


            
                    coating_loss_today += coating_loss_from_cleaning
                    roughness_increase_today += roughness_increase_from_cleaning
                    biocide_released_today += biocide_loss_from_cleaning


                    self.last_cleaning = day
                    self.num_cleanings += 1
                     

            elif self.cleaning_type == "Reactive Cleanings":

                if (power_change_today + roughness_power_increase) > self.reactive_cleaning:
                #if power_changes[day - 1] > self.reactive_cleaning:
                # Convert 'day' to a datetime object
                    current_date = start_date + pd.Timedelta(days=day)
                    print(f"{self.reactive_cleaning}% Power reduction observed achieved on day {day}, or {current_date.strftime('%Y-%m-%d')}")
                    print(f"the power checked today is {power_change_today+ roughness_power_increase}")
                    print(f"the power checked yesterday is {power_changes[day-1]}")
                    print(f"the roughness power increase is {roughness_power_increase}")
                    #power_reduction_cleaning = (-self.out_of_dock_savings * 100) - (1 - self.power_reduction_from_cleaning)
                    power_reduction_cleaning = (-self.out_of_dock_savings * 100)    
                    power_change_today = power_reduction_cleaning


                    coating_loss_from_cleaning = (self.cleaning_thickness_impact * float(growth_level/100))
                    roughness_increase_from_cleaning = ((self.cleaning_thickness_impact * 0.5)* float((growth_level/100)))
                    biocide_loss_from_cleaning = self.biocide_removed_from_cleaning * float((growth_level/100))


                
                    coating_loss_today += coating_loss_from_cleaning
                    roughness_increase_today += roughness_increase_from_cleaning
                    biocide_released_today += biocide_loss_from_cleaning



                    """coating_thickness[day] = coating_thickness[day - 1] - self.cleaning_thickness_impact
                    coating_roughness[day] = coating_roughness[day - 1] + self.cleaning_thickness_impact * 0.5"""
                    self.last_cleaning = day
                    self.num_cleanings += 1
                    self.cleaning_events.append(day)

            # one cleaning frequency. clean every n months
            elif self.cleaning_type == "Periodic Cleanings":
                # otherwise, if we are cleaning on a regular basis, check to see if the current day is a cleaning day
                if self.cleaning_frequency == 0:
                    pass
                else:
                    # Convert 'day' to a datetime object
                    current_date = start_date + pd.Timedelta(days=day)

                    # Check if current date is the first of the month
                    if current_date.day == 1:
                        # Calculate the total months since the start of the dataset
                        total_months = (
                                               current_date.year - start_date.year) * 12 + current_date.month - start_date.month


                        print(f"the total_months is {total_months}")
                        print(f"the cleaning frequency is {self.cleaning_frequency}")
                        print(f"the result of the modulo is {total_months % self.cleaning_frequency}")


                        # Check if the current month aligns with the cleaning frequency
                        if total_months % self.cleaning_frequency == 0:
                            # Your logic here, this is where the cleaning should be scheduled
                            print(f"Cleaning scheduled on {current_date.strftime('%Y-%m-%d')}")
                            # Apply improvement from cleaning
                            
                            """cleaning_improvement = (self.increase_from_cleaning)
                            power_changes[day] -= cleaning_improvement"""
                            #if (1 + power_changes[day-1] / 100) * self.average_power > self.power_out_of_dock: #tbh not sure exactly how it works but it prevents cleanings from happening when there is no excess growth?

                            self.last_cleaning = day
                            if self.debug:
                                print(f"Cleaning applied on day {day}")

                            power_reduction_cleaning = (-self.out_of_dock_savings * 100) 
                            power_change_today = power_reduction_cleaning

                            #coating_loss_from_cleaning = (self.cleaning_thickness_impact)
                            #roughness_increase_from_cleaning = ((self.cleaning_thickness_impact * 0.5))

                            #coating_thickness[day] = coating_thickness[day-1] - (self.cleaning_thickness_impact * float(growth_level/100))
                            #coating_roughness[day] = coating_roughness[day-1] + ((self.cleaning_thickness_impact * 0.5)* float((growth_level/100)))

                            coating_loss_from_cleaning = (self.cleaning_thickness_impact * float(growth_level/100))
                            roughness_increase_from_cleaning = ((self.cleaning_thickness_impact * 0.5)* float((growth_level/100)))
                            biocide_loss_from_cleaning = self.biocide_removed_from_cleaning * float((growth_level/100))

                            coating_loss_today += coating_loss_from_cleaning
                            roughness_increase_today += roughness_increase_from_cleaning
                            biocide_released_today += biocide_loss_from_cleaning



                            self.num_cleanings += 1
                            self.cleaning_events.append(day)

            if self.debug:
                # print out the individual contributions to the power change
                print("------------------------------")
                print(f"The day is {day}")
                print(f"Power change from roughness is {roughness_power_increase}")
                print(f"Power change from cleaning is {power_reduction_cleaning}")
                print(f"Power change from growth is {growth_power_increase}")
                print(f"Total power increase is {power_change_today}")
                print("------------------------------")

            coating_thickness[day] = coating_thickness[day-1] - coating_loss_today
            coating_roughness[day] = coating_roughness[day-1] + roughness_increase_today

            coating_thickness_daily_loss.append(coating_loss_today)

            # the coating cant go below 0 microns thickness
            if coating_thickness[day] < 0:
                coating_thickness[day] = 0

            """if (self.last_cleaning == day) or (self.last_cleaning == day-1) or (self.last_cleaning == day+1) or (self.last_cleaning == day-2) or (self.last_cleaning == day+2) :
                print(f"DAY {day}")
                print(f"Coating thickness yesterday was {coating_thickness[day-1]}")
                print(f"Coating thickness reduction today is {coating_loss_today}")
                print(f"Coating thickness reduction due to cleanings today is {coating_loss_from_cleaning}")
                print(f"Coating thickness today is {coating_thickness[day]}")"""

            #apply the power loss due to the coating roughness, 20 micron increase in roughness is a 1% power loss
            
            roughness_power_increase = (((coating_roughness[day]) - self.initial_roughness) / 20)


            power_change_today += roughness_power_increase

            r"""# check to see if the power change today is lower than the out of dock savings. this happens weirdly with the period cleanings. this is a hard coded fix
            if power_change_today < (-self.out_of_dock_savings * 100):
                power_change_today = (-self.out_of_dock_savings * 100)"""
            

                

            # Update the power change for the day
            # power_changes[day] = power_changes[day-1] + power_change_today
            power_changes[day] = power_change_today

            if day in self.cleaning_events:
                print(f"Power change today is {power_change_today}")
            
            

            #calculated the normalized speed (average power is power at max speed, bad name I know)
            engine_load = speeds[day] / self.max_speed

            # Calculate power output : new_power_output = base_power_usage * (1 + power_change/100)
            power_output[day] = (self.average_power * (1 + power_changes[day] / 100)) * engine_load

            biofouling_growth_level[day] = growth_level

            biocide_levels[day] = biocide_levels[day-1] - biocide_released_today

            if biocide_levels[day] < 0:
                biocide_levels[day] = 0

            if day in self.cleaning_events:
                print("About to apply power changes !!!!!!!!!!!")
                print(f"power change from cleaning is {power_reduction_cleaning}")
                print(f"Power change today is {power_change_today}")
                print(f"roughness power increase is {roughness_power_increase}")
                #breakpoint()

            if self.debug:
                print(f"Power change yesterday was {power_changes[day - 1]} - {self.coating_type}")
                print(f"The power change for day {day} is {power_changes[day]} - {self.coating_type}")
                print(f"The power output for day {day} is {power_output[day]} - {self.coating_type}")

        # has to happen after the method because the conditional statements will change the value of the variable
        if self.cleaning_type == "Reactive Cleanings":
            self.cleaning_type = f"Reactive Cleanings at {self.reactive_cleaning}%"

        if self.cleaning_type == "Fixed Cleanings":
            self.cleaning_type = f"Fixed Cleanings at {self.cleaning_frequency} days"

        if self.cleaning_type == "Periodic Cleanings":
            if self.cleaning_frequency == 0:
                self.cleaning_type = "No Cleanings"
            else:
                self.cleaning_type = f"Periodic Cleanings {self.cleaning_frequency} months"

        # kWh = sum(day1kW+day2kW+day3kW...)*24
        # total_energy = sum(power_output*24) * self.activity_rate
        total_energy = self.calculate_total_energy_used(power_output)

        #use this to calculate cleaninings haha
        self.num_cleanings = len(self.cleaning_events)

        print(f"cleaning events is {self.cleaning_events}")
        

        self.cleaning_offhire_cost = self.num_cleanings * self.offhire_cost_per_cleaning

    
        # in kWh
        self.total_energy = round(total_energy, 2)

        # convert to a string with mWh
        self.total_energy = f"{round(self.total_energy / 1000, 3)} mWh"


        speed_changes = power_changes / 3

        fuel_consumptions_daily = []
        speed_actual = []
        #calculate the daily fuel consumption and actual speed
        for i, daily_power_output in enumerate(power_output):
            fuel_consumptions_daily.append((daily_power_output * 24)/self.energy_density)
            speed_actual.append(speeds[i]* ((100-speed_changes[i])/100))




        if self.distance is None:
            print(f"No distance provided for CII calculation, using the real speed to calculate the distance")

            #calculate the distance using the real speed
            self.total_distance = 0

            for i, speed in enumerate(speed_actual):
                self.total_distance += speed * 24
            
            #get the yearly average distance
            self.distance = self.total_distance/(self.days_in_sim/365)

        #get the average yearly fuel consumption for each year in the simulation
        year_1_fuel_consumption = sum(fuel_consumptions_daily[:365])
        year_2_fuel_consumption = sum(fuel_consumptions_daily[365:730])
        year_3_fuel_consumption = sum(fuel_consumptions_daily[730:1095])
        year_4_fuel_consumption = sum(fuel_consumptions_daily[1095:1460])
        year_5_fuel_consumption = sum(fuel_consumptions_daily[1460:1825])

        #assemble the fuel data for each year as fuelData = [{"HFO" : 2105.48},{"HFO" : 2126.54},{"HFO" : 2147.80},{"HFO" : 2169.28},{"HFO" : 2190.98}]
        
        self.fuel_data = [{self.fuel_type : year_1_fuel_consumption},{self.fuel_type : year_2_fuel_consumption},
                          {self.fuel_type : year_3_fuel_consumption},{self.fuel_type : year_4_fuel_consumption},
                          {self.fuel_type : year_5_fuel_consumption}]
        
        if self.dwt is None:
            print("No DWT provided. Need this for CII calculation")
            
            
            
        if self.vessel_type is None:
            print("No vessel type provided. Need this for CII calculation")
            
        #print all of the cii data
        print(f"Vessel type is {self.vessel_type}")
        print(f"Coating type is {self.coating_type}")
        print(f"DWT is {self.dwt}")
        print(f"Distance is {self.distance}")
        print(f"Fuel data is {self.fuel_data}")


        self.cii_label = f"{self.coating_type}\n{self.cleaning_type}"
        cii_sim = cii.CII(self.vessel_type,self.cii_label,self.dwt,self.distance,self.fuel_data)

        self.cii_results = cii_sim.results

        print(f"Model results are at {cii_sim.results_path}")


            
            
            


        #=I2*((100-J2)/100)


        #take the average of the non zero values to get the operating fuel consumption
        fuel_consumptions_daily_no_zeros = [x for x in fuel_consumptions_daily if x != 0]
        fuel_consumptions_daily_avg = np.mean(fuel_consumptions_daily_no_zeros)
        self.operating_daily_fuel_consumption = round(fuel_consumptions_daily_avg, 2)

        # total fuel mass = total energy / energy density
        self.total_fuel_mass = round(total_energy / self.energy_density, 2)

        self.average_daily_fuel_burn = round(self.total_fuel_mass / 1825, 2)

        # total fuel cost = total fuel mass * fuel cost
        self.total_fuel_cost = round(self.total_fuel_mass * self.fuel_cost, 2)
        self.average_daily_fuel_cost = round(self.total_fuel_cost / 1825, 2)

        self.total_cleaning_cost = round(self.num_cleanings * self.cleaning_cost, 2)

        if self.cleaning_subscription is not None:
            #if we are using a subscription model for cleaning, then we will use the subscription cost
            self.total_cleaning_cost = self.cleaning_subscription
            self.cleaning_cost = self.cleaning_subscription

        self.total_cost_of_ownership = round(self.total_fuel_cost + self.total_cleaning_cost + self.coating_cost,
                                             2)  # should have the cost of the coating
        
        self.total_cost_of_ownership += self.total_shipyard_cost #add the total shipyard cost to the total cost of ownership
        self.total_cost_of_ownership += self.cleaning_offhire_cost #add the total offhire cost to the total cost of ownership

        self.total_fuel_cost = f"{round(self.total_fuel_cost / 1000000, 3)}M"

        # total cleaning cost = number of cleanings * cleaning cost

        # convert total cost of ownership to a string formatted in millions
        self.total_cost_of_ownership = f"{round(self.total_cost_of_ownership / 1000000, 3)}M$ USD"

        print(f"Total energy is {total_energy}kHw")
        print(f"Total fuel mass is {self.total_fuel_mass}t")
        print(f"Total fuel cost is {self.total_fuel_cost}USD")
        print(f"Total number of cleanings is {self.num_cleanings}")
        print(f"Total cleaning cost is {self.total_cleaning_cost}USD")
        print(f"Total cost of ownership is {self.total_cost_of_ownership}USD")
        print(f"self.t_modifier is {self.t_modifier}")
        print(f"self.activity_rate is {self.activity_rate}")
        print(f"self.max_speed is {self.max_speed}")
        print(f"self.self_cleaning is {self.self_cleaning}")
        print(f"self.cleaning_thickness_impact is {self.cleaning_thickness_impact}")

        average_power = round(np.mean(power_changes), 2)
        self.percent_speed_loss = round(abs(-self.out_of_dock_savings* 100 - average_power)/ 3, 2)


        Reference_Period=power_changes[:365]
        Evaluation_Period=power_changes[365:]
        self.reference_speed=round(np.nanmean(Reference_Period)/3,3)
        self.evaluation_speed=round(np.nanmean(Evaluation_Period)/3,3)
        self.iso_speed_loss=round(self.evaluation_speed-self.reference_speed,3)

        #make a new list for the speed changes 




        #this is important ^ we are defining the percent speed loss to be the difference between the out of dock savings and the average power through the sim. The out of dock savings
        #are positive and need to be multiplied by 100 to match the power changes.

        print(f"THIS IS THE AVERAGE POWER {average_power} and this is the percent speed loss {self.percent_speed_loss}")
        print(f"AND THIS IS THE OUT OF DOCK SAVINGS {self.out_of_dock_savings * 100}")

        print(f"This is the length of speeds {len(speeds)}")
        print(f"this is the length of power output {len(coating_thickness_daily_loss)}")
        # Create DataFrame
        df = pd.DataFrame({
            'date': dates,
            'power_change': power_changes,
            'power_output': power_output,
            'total_energy': total_energy,
            'coating_thickness': coating_thickness,
            'coating_roughness': coating_roughness,
            "fuel_consumption": fuel_consumptions_daily,
            "speed" : speeds,
            "speed_change": speed_changes,
            "speed_actual" : speed_actual,
            "biofouling_growth_level": biofouling_growth_level,
            "coating_thickness_daily_loss": coating_thickness_daily_loss,
            "biocide_level": biocide_levels
        })

        return df

    
    import matplotlib.pyplot as plt



def plot_results_obj_list(models, col='power_output', no_power_details=True, growth_type="linear", save=False,
                          debug=False,show = True,show_table = True):
    
    
    """
    Plots the results of the 5 year simulation from a list of tco_model instances side by side with respective tables.

    :param models: List of tco_model objects
    :param col: the column to plot (power_output or power_change)
    :return: None
    """
    if debug:
        print(f"Debugging with {len(models)} models.")

    r"""for model in models:
        #load the coating details for each model
        model.load_coating_details(model.coating_type)"""

    if show_table:
        plot_dpi = 78
        fig, axs = plt.subplots(1, 2, figsize=(40, 16), gridspec_kw={'width_ratios': [3, 1]}, dpi=plot_dpi)
    else:
        plot_dpi = 200
        fig, axs = plt.subplots(1, 1, figsize=(30, 16), dpi=plot_dpi)
        axs = [axs]

    precalculated_model_data = []

    ref_start = 0.045
    ref_end = 0.227

    eval_start = 0.227
    eval_end = 0.958
    text_offset = 0.1  # Adjust this value based on your scale and preference

    # Define your date range
    start_date = pd.Timestamp('2020-01-01')
    end_date = pd.Timestamp('2025-01-01')

    # Create a date range for plotting
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')


    # Iterate through models and plot each one's data
    for i, model in enumerate(models):
        model_data = model.run_5y()
        axs[0].plot(model_data['date'], model_data[col], label=model.coating_type + f"\n{model.cleaning_type} (Model #" + str(i + 1) + ")")
        precalculated_model_data.append(model_data)

        model.biofouling_delay = str(round(model.biofouling_delay * 100)) + "%"



        #if we are plotting the speed loss, plot horizontal lines for the reference and evaluation speeds. the reference speed should be plotted over the first year and the evaluation speed should be plotted over the next 4 years
        if col == "speed_change":
            axs[0].axhline(y=model.reference_speed, color='r', linestyle='--',  xmin=ref_start, xmax=ref_end)
            axs[0].axhline(y=model.evaluation_speed, color='g', linestyle='--', xmin=eval_start, xmax=eval_end)

            #if two or more of the values are the same, bundle them into the same text as to not clutter the plot


            # Adding text labels near the reference and evaluation lines in data coordinates
            axs[0].text(date_range[int(ref_start * len(date_range))], model.reference_speed, f'{model.reference_speed:.2f} (ref) m-{i+1}', 
                        verticalalignment='bottom', horizontalalignment='right', color='r')
            axs[0].text(date_range[int(eval_end * len(date_range))], model.evaluation_speed, f'{model.evaluation_speed:.2f} (eval) m-{i+1}', 
                        verticalalignment='bottom', horizontalalignment='left', color='g')



    axs[0].set_xlabel('Date')
    axs[0].set_ylabel(col.replace('_', ' ').title())
    axs[0].set_title(f'{col.replace("_", " ").title()} Over Time')
    axs[0].grid(True)
    axs[0].legend()

    if col == 'power_output':
        axs[0].set_ylabel('Power Output (kW)')
    elif col == "power_change":
        axs[0].set_ylabel('Power Change (%)')


    if show_table:
        # Initialize table data with headers
        table_data = [["Variable"] + [f"Model {i + 1} Value" for i in range(len(models))]]


        # Dynamically generate table rows for each attribute
        attributes = ["coating_type","vessel_name", "region", "coated_sqm","fouling_type", "activity_rate","max_speed","growth_type", "cleaning_type","num_cleanings",
                    "average_power", "daily_power_loss","vessel_efficiency",
                    "fuel_type", "total_energy", "total_fuel_mass", "total_fuel_cost", "sfoc",
                    "average_daily_fuel_burn", "operating_daily_fuel_consumption","average_daily_fuel_cost",
                    "coating_cost", 
                    "cleaning_cost", "cleaning_offhire_cost","total_cleaning_cost", 
                    "application_offhire_cost","surface_prep_cost","washing_cost","application_cost","shipyard_rent_cost","total_shipyard_cost",
                    "total_cost_of_ownership",
                    "power_output_mean", "power_output_std_dev",
                    "power_change_mean", "power_change_std_dev", "percent_speed_loss",
                    "reference_speed","evaluation_speed","iso_speed_loss"]

        if no_power_details:
            attributes = ["coating_type", "cleaning_frequency", "average_power", "daily_power_loss",
                        "fuel_type", "total_energy", "total_fuel_mass", "total_fuel_cost",
                        "power_reduction_from_cleaning",
                        "average_daily_fuel_burn", "average_daily_fuel_cost", "num_cleanings",
                        "cleaning_cost", "total_cleaning_cost", "total_cost_of_ownership"]

        for attr in attributes:
            row = [attr.replace('_', ' ').title()]
            for i, model in enumerate(models):
                model_data = precalculated_model_data[i]
                if attr in ['total_fuel_mass', 'average_daily_fuel_burn',
                            'average_daily_fuel_cost', 'power_output_mean', 'power_output_std_dev',
                            'power_change_mean', 'power_change_std_dev']:

                    if attr == "power_change_mean":
                        val = round(model_data["power_change"].mean(), 2)
                    elif attr == "power_change_std_dev":
                        val = round(model_data["power_change"].std(), 2)
                    elif attr == "power_output_mean":
                        val = round(model_data["power_output"].mean(), 2)
                    elif attr == "power_output_std_dev":
                        val = round(model_data["power_output"].std(), 2)
                    else:

                        # Special handling for numeric data
                        val = round(
                            getattr(model, attr, model_data[col].mean() if 'mean' in attr else model_data[col].std()), 2)
                else:
                    # Direct attribute access
                    val = getattr(model, attr, 'N/A')
                row.append(val)
            table_data.append(row)

        # Add table on the second axis
        axs[1].axis('tight')
        axs[1].axis('off')
        table = axs[1].table(cellText=table_data, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)  # Adjust scale to fit models' data

        # Dynamically adjust column width
        table.auto_set_column_width(col=list(range(len(models) + 1)))
    else:
        axs[0].legend(fontsize=24)
        axs[0].set_xlabel('Date', fontsize=24)
        axs[0].set_ylabel(col.replace('_', ' ').title(), fontsize=24)
        axs[0].set_title(f'{col.replace("_", " ").title()} Over Time', fontsize=28)
        axs[0].tick_params(axis='both', which='major', labelsize=20)

    # Adjust layout to prevent overlap
    plt.tight_layout()


    if show:
        # Show the plot
        plt.show()

    if save:
        """
        Save the figure to a file
        """
        filename = f"Plots/{col}_results_{growth_type}.png"
        fig.savefig(filename, dpi=plot_dpi)

    return fig


    """for model in models:
        #delete all model objects 
        del model"""


def plot_coating_details(models, metrics=['power_change', 'coating_thickness',
                                          'coating_roughness',"biofouling_growth_level"], save=False, debug=False,show = True):
    """
    Plots the specified metrics of the coating details over 5 years from a list of model instances.

    :param models: List of model objects
    :param metrics: List of metrics to plot from the model's DataFrame
    :param save: Boolean indicating whether to save the plots
    :param debug: Boolean indicating whether to print debug information
    :return: None
    """
    if debug:
        print(f"Debugging with {len(models)} models and metrics {metrics}.")

    for model in models:
        #load the coating details for each model
        model.load_coating_details(model.coating_type)

    precalculated_model_data = []

    # Iterate through models and plot each one's data
    for i, model in enumerate(models):
        model_data = model.run_5y()
        precalculated_model_data.append(model_data)

    # Number of metrics determines the number of subplots
    num_metrics = len(metrics)
    fig, axs = plt.subplots(num_metrics, 1, figsize=(15, 5 * num_metrics), dpi=400)

    # Ensure axs is an array even when plotting a single metric
    if num_metrics == 1:
        axs = [axs]

    for metric in metrics:
        for i, model in enumerate(models):
            model_data = precalculated_model_data[i]
            ax = axs[metrics.index(metric)]
            ax.plot(model_data['date'], model_data[metric], label=f"{model.coating_type}\n{model.cleaning_type} (Model #{i + 1})")
            ax.set_xlabel('Date')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'{metric.replace("_", " ").title()} Over Time')
            ax.grid(True)
            ax.legend(fontsize=8)

    # Adjust layout to prevent overlap
    plt.tight_layout()

    if save:
        for metric in metrics:
            filename = f"Plots/{metric}_details_over_time.png"
            plt.savefig(filename, dpi=fig.dpi)
            if debug:
                print(f"Saved plot for {metric} to {filename}")

    if show:
        # Show the plot
        plt.show()

    for model in models:
        #delete all model objects 
        del model

    return fig

        


def generate_speeds(activity_percentage, max_speed, total_days):
    """
    Generates an array representing vessel speed over a specified number of days,
    with even distribution of active and inactive periods based on activity percentage.

    Parameters:
    - activity_percentage: The percentage of days the vessel is active (0-1).
    - max_speed: The maximum speed the vessel operates at.
    - total_days: Total days for the speed profile.

    Returns:
    - np.array: Array of daily speeds.
    """
    # Calculate the total number of active days
    active_days = int(total_days * activity_percentage)
    
    # Determine speed for each day
    speed_profile = np.zeros(total_days)
    active_indices = np.linspace(0, total_days-1, active_days, dtype=int)
    speed_profile[active_indices] = max_speed

    return speed_profile



def cii_table(models, debug=True, save=False,show = True):
    if debug:
        print(f"Debugging cii_table with {len(models)} models")

    # Load the coating details for each model
    for model in models:
        model.load_coating_details(model.coating_type)

    cii_tables = []
    model_names = []


    """

    0	CII Required
    1	CII Attained
    2	CII Ratio
    3	CII Rating

    """
    # Iterate through models and get CII results
    for i, model in enumerate(models):
        model_data = model.run_5y()
        # Extract relevant data
        cii_attained = model.cii_results.iloc[1, 7:13].values  # CII Attained values
        cii_req = model.cii_results.iloc[0, 7:13].values  # CII Required values

        cii_ratings = model.cii_results.iloc[3, 7:13].values   # CII Ratings
        cii_years = model.cii_results.columns[7:13]      # CII Years
        combined_data = [f"Att: {attained} Req: {required}\n({rating})" for attained, year, required,rating in zip(cii_attained,cii_years,cii_req, cii_ratings)]
        cii_tables.append(combined_data)
        model_names.append(model.cii_label)

    if debug:
        print(f"Model names are {model_names}")
        print(f"Model CII tables are {cii_tables}")

    # Create a DataFrame for the combined data
    combined_df = pd.DataFrame(cii_tables, columns=["2025", "2026", "2027", "2028", "2029","2030"], index=model_names)

    # Define a function to color code cells based on CII Rating
    def color_code_cell(value):
        rating = value.split('(')[-1][0]  # Extract the CII rating (A, B, C, D, E)
        color_map = {
            'A': '#00FF00',  # Green
            'B': '#ADFF2F',  # GreenYellow
            'C': '#FFFF00',  # Yellow
            'D': '#FFA500',  # Orange
            'E': '#FF4500'   # OrangeRed
        }
        return color_map.get(rating, "")
    

    # Calculate row heights based on the number of lines in each cell
    row_heights = []
    for row in combined_df.values:
        max_lines = max([len(str(cell).split('\n')) for cell in row])
        row_heights.append(max_lines)

    if debug:
        print(f"Here are the row heights {row_heights}")

    # Create a matplotlib figure
    fig, ax = plt.subplots(figsize=(12, 8), dpi=400)  # Adjust the size as needed
    ax.axis('off')
    ax.axis('tight')

    # Create a table in the plot
    table = ax.table(cellText=combined_df.values,
                     colLabels=combined_df.columns,
                     rowLabels=combined_df.index,
                     cellLoc='center',
                     loc='center')
    print(f"exporing the combined df {combined_df}")
    combined_df.to_csv(r"C:\Dashboard\tco_ui\tco_ui\tco\ui\CII Results\cii_table_test.csv")


    # Apply color coding to the cells based on the CII Rating
    for (i, j), cell in table.get_celld().items():
        if i > 0 and j >= 0:  # Skip the header cells
            value = combined_df.iat[i-1, j]  # Access cell value
            rating = color_code_cell(value)  # Get color for the rating
            if debug:
                print(f"At cell ({i-1},{j-1}) with value: '{value}'. Rating extracted: '{value.split('(')[-1][0]}', Color applied: {rating}")
            cell.set_facecolor(rating)  # Apply color


    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)

    # Scale row heights
    for i, height in enumerate(row_heights):
        table.scale(1, 1.1 * height)

    fig.tight_layout()

    if save:
        output_dir = "CII Results/Tables"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "cii_table.png")
        fig.savefig(output_path)
        if debug:
            print(f"Table saved to {output_path}")

    if show:
        plt.show()

    return fig




import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import traceback

def create_report(models, output_path='output.pdf', debug=False):
    """
    Create a PDF report with model results. The report will contain three pages:
    1. Model Results
    2. CII Table
    3. Coating Details

    We we will take in a list of models, and then run the plotting methods (each of which run the models) have each of them return the plot fig. We will
    save the resulting figs, and save them to a pdf.

    Parameters:
    model_results_fig (matplotlib.figure.Figure): Figure for model results (first page).
    cii_table_fig (matplotlib.figure.Figure): Figure for CII table (second page).
    coating_details_fig (matplotlib.figure.Figure): Figure for coating details (third page).
    output_path (str): Path to save the PDF file.
    debug (bool): If True, print debug statements.
    """

    model_results_fig = None
    cii_table_fig = None 
    coating_details_fig = None

    #make a deep dopy version of each of the models for each plot
    models_results = [copy.deepcopy(model) for model in models]
    models_cii = [copy.deepcopy(model) for model in models]
    models_coating_details = [copy.deepcopy(model) for model in models]


    model_results_fig = plot_results_obj_list(models_results, col='power_change', no_power_details=False, save=False, debug=debug,show = False,show_table = False)
    cii_table_fig = cii_table(models_cii, save=False, debug=debug,show = False)
    coating_details_fig = plot_coating_details(models_coating_details, save=False, debug=debug,show = False)


    if debug:
        print(f"Model results fig is {model_results_fig}")
        print(f"CII table fig is {cii_table_fig}")
        print(f"Coating details fig is {coating_details_fig}")
        

    def add_scaled_figure(fig, pdf, page,scale=1.0, x=5.5, y=4.25, debug=False):
        """
        Add a scaled figure to a letter-sized (8.5x11) page in landscape orientation to a PDF.

        Parameters:
        fig (matplotlib.figure.Figure): Figure to be added.
        pdf (PdfPages): PdfPages object to save the page.
        scale (float): Scale factor for the figure size.
        x (float): X-axis position for the figure center.
        y (float): Y-axis position for the figure center.
        debug (bool): If True, print debug statements.
        """
        if debug:
            print(f"Adding scaled figure to the PDF with scale {scale}, x {x}, y {y}")

        full_page_fig = plt.figure(figsize=(11, 8.5))

        if page == 1:
            cost_assumptions = models[0].get_cost_assumptions()

            # Convert the cost assumptions dictionary to a formatted string
            cost_assumptions_text = format_assumptions(cost_assumptions, debug=debug)

            #add the cost assumptions
            full_page_fig.text(0.705, 0.4, cost_assumptions_text, ha='left', va='center', fontsize=9)


        # Compute the new width and height based on the scale factor
        width, height = fig.get_size_inches()
        scaled_width = width * scale
        scaled_height = height * scale

            # Set the size of the full-page figure in pixels
        full_page_fig.set_size_inches(11, 8.5)
        full_page_fig.dpi = fig.dpi

        # Calculate the position to place the scaled figure on the full-page figure
        x_pixels = x * fig.dpi
        y_pixels = (8.5 - y) * fig.dpi - scaled_height * fig.dpi

        if debug:
            print(f"x_pixels: {x_pixels}, y_pixels: {y_pixels}")

        # Create a new Axes object at the specified position with no frame
        ax = full_page_fig.add_axes([x_pixels / (11 * fig.dpi), 
                                    y_pixels / (8.5 * fig.dpi), 
                                    scaled_width / 11, 
                                    scaled_height / 8.5], 
                                    frameon=False)
        
        #remove the ticks from the axes
        ax.set_xticks([])
        ax.set_yticks([])

        # Transfer the content of the original figure to the new Axes object
        fig_canvas = fig.canvas
        fig_canvas.draw()
        renderer = fig_canvas.get_renderer()

        # Render the original figure into the new Axes object
        ax.imshow(fig_canvas.buffer_rgba(), aspect='auto', extent=(0, scaled_width, 0, scaled_height))

        #tight layout
        full_page_fig.tight_layout()

        # Save the full page figure to the PDF
        pdf.savefig(full_page_fig)
        plt.close(full_page_fig)

    def add_text_to_figure(fig, text, position=(0.5, 0.9), font_size=12, debug=False):
        """
        Add text to an existing figure.

        Parameters:
        fig (matplotlib.figure.Figure): Figure to add text to.
        text (str): Text to be added.
        position (tuple): (x, y) position of the text.
        font_size (int): Font size of the text.
        debug (bool): If True, print debug statements.
        """
        if debug:
            print(f"Adding text to figure at position {position} with font size {font_size}")

        # Create a new Axes object to hold the text
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])

        # Add the text
        ax.text(position[0], position[1], text, fontsize=font_size, ha='center', va='center', wrap=True)


    def format_assumptions(assumptions, debug=False):
        try:
            formatted_string = "                         Cost Assumptions\n\n"
            formatted_string += " • Shipyard rate for washing: {}\n".format(assumptions.get("washing_rate", "N/A"))
            formatted_string += " • Shipyard rate for surface preparation: {}\n".format(assumptions.get("surface_prep_rate", "N/A"))
            formatted_string += " • Shipyard rate for paint application: {}\n".format(assumptions.get("application_rate", "N/A"))
            formatted_string += " • Yard rent: {}\n".format(assumptions.get("yard_rent", "N/A"))
            formatted_string += " • Off-hire cost: {}\n".format(assumptions.get("application_offhire_cost", "N/A"))
            formatted_string += " • Underwater hull cleaning cost: {}\n".format(assumptions.get("washing_cost", "N/A"))
            formatted_string += " • Fuel price: {}/ton ({})\n".format(assumptions.get("fuel_cost", "N/A"), assumptions.get("fuel_type", "N/A"))
            return formatted_string
        except Exception as e:
            if debug:
                print("An error occurred while formatting assumptions: {}".format(e))
                import traceback
                traceback.print_exc()
            return "Error in formatting assumptions."


    try:

        cost_assumptions = models[0].get_cost_assumptions()

        # Convert the cost assumptions dictionary to a formatted string
        cost_assumptions_text = format_assumptions(cost_assumptions, debug=debug)


        print(f"Here are the cost assumptions  \n{cost_assumptions}")

        with PdfPages(output_path) as pdf:
            if debug:
                print(f"Saving model results figure to the first page of {output_path}")
            # First page - Model Results
            add_scaled_figure(model_results_fig, pdf, scale=0.25, x=0.25, y=4.25, page = 1,debug=debug)

            
            if debug:
                print(f"Saving CII table figure to the second page of {output_path}")
            # Second page - CII Table
            add_scaled_figure(cii_table_fig, pdf, scale=0.75, x=2, y=2.5, page = 2,debug=debug)
            
            if debug:
                print(f"Saving coating details figure to the third page of {output_path}")
            # Third page - Coating Details
            add_scaled_figure(coating_details_fig, pdf, scale=0.40, x=0.25, y=0.25, page = 3, debug=debug)
            
            

            if debug:
                print(f"Successfully saved all figures to {output_path}")
                
    except Exception as e:
        if debug:
            print("An error occurred while saving the PDF:")
            print(e)
            traceback.print_exc()



