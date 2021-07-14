import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import datetime
import pprint

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import traceback


class SfHealth:
    def __init__(self, env,instance_name, domain="status.salesforce.com", driver_type="chrome", driver_path="/Users/gokadroid/drivers/chromedriver"):
        self.env=env
        self.instance_name=instance_name
        self.domain=domain
        self.url=None
 
        #Some hardcodes
        self.uri_prefix="instances"
        self.uri_suffix=""
        self.overall_health_filter="div.sc-iueMJG.gNlGiH"
        self.service_filter="div.sc-gGuQiZ.fAXLLe"

        self.ok_health="OK"
        self.notok_health="NOT-OK"
        
        self.instance_attr="[data-testid='instance-info']"
        self.instance_meta=[ 'Version', 'Region', 'Maintenance Window' ]

        self.delimiter=","
        self.delay=10


        #Driver vars for Chrome
        self.driver_path=driver_path
        self.driver_type=driver_type
        self.driver=None
        self.driver_options=None
        self.driver_option_args=['--no-sandbox', '--disable-dev-shm-usage', 'headless']

        self.health_check={}

        #Form the url to use
        self.form_url()

    #Format the key for dictionary
    def format_key(self,key_str):
        return key_str.lower().strip().replace(' ', '_')


    #Initialize the driver for chrome 
    def initialize_chrome_driver(self):
        self.driver_options = Options()
        for do_arg in self.driver_option_args:
            self.driver_options.add_argument(do_arg)
        self.driver = webdriver.Chrome(options=self.driver_options, executable_path=self.driver_path)
        #https://stackoverflow.com/a/34838339/14885821
        
        self.driver.get(self.url) 




    #Make the callable url from the variables
    def form_url(self):
        protocol=""
        url_sep="/"
        if "http://" not in self.domain and "https://" not in self.domain:
            protocol="https://"


        self.url=protocol+str(self.domain)

        if self.uri_prefix != "":
            self.url+=str(url_sep) + str(self.uri_prefix) + str(url_sep) + str(self.instance_name)

        if self.uri_suffix != "":
            self.url+=str(url_sep) + str(self.uri_suffix)


    #Get overall health of the instance
    def get_overall_health(self):
        tag=self.overall_health_filter
        delimiter=self.delimiter


        div_table = self.driver.find_element_by_css_selector(tag)
        health_elements = div_table.find_elements_by_tag_name('span')
        row=""
        for span in health_elements:
            if row == "":
                row+=span.text
            elif span.text == "Available" and self.ok_health not in row:
                row+=delimiter+self.ok_health
            elif span.text != "Available" and self.ok_health not in row:
                row+=delimiter+self.notok_health

        return row


    #Get instance services health
    def get_services_health(self):
        tag=self.service_filter
        delimiter=self.delimiter

        service_status=[]
        div_table = self.driver.find_elements_by_css_selector(tag)
        for div_elemi, div_element in enumerate(div_table):
            #print(str(div_elemi))
            div_elements = div_element.find_elements_by_tag_name('div')
            row=""
            for divsi, divs in enumerate(div_elements):
                div = divs.find_elements_by_tag_name('div')
                #print("|--> divs[",str(divsi),"]")
                #service=""
                #available=False
                if len(div) > 1:

                    service=str(div[0].find_elements_by_tag_name('span')[0].text)

                    status=div[1].find_elements_by_tag_name('span')[0].find_elements_by_css_selector("use")[0].get_attribute('xlink:href')

                    if '#healthy' in status:

                        row=service+str(delimiter)+self.ok_health
                    elif '#unhealthy' in status:

                        row=service+str(delimiter)+self.notok_health
                    service_status.append(row)

        return service_status



    #Get instance meta data
    #https://stackoverflow.com/a/26306203/14885821
    def get_instance_details(self):
        tag="div"
        attr="[data-testid='instance-info']"
        delimiter=self.delimiter

        wrapped_div = self.driver.find_elements_by_css_selector(tag+attr)
        #print(tag+attr)
        #print(len(wrapped_div))
        instance_details = {}
        vstr="Version"
        rstr="Region"
        mstr="Maintenance Window"

        #Email
        #https://www.kite.com/python/answers/how-to-check-if-a-string-contains-an-element-from-a-list-in-python

        for divsi, divs in enumerate(wrapped_div):
           int_div=divs.find_elements_by_css_selector('div')
           for idi, id in enumerate(int_div):
               if vstr in id.text:
                   instance_details[self.format_key(vstr)]=id.text.replace(vstr, '').replace('\n', '').strip()
               elif rstr in id.text:
                   instance_details[self.format_key(rstr)]=id.text.replace(rstr, '').replace('\n', '').strip()
               elif mstr in id.text:
                   instance_details[self.format_key(mstr)]=id.text.replace(mstr, '').replace('Help', '').replace('\n', ' ').strip()
               else:
                   continue

        return instance_details



    def perform_health_check(self):
        delimiter=self.delimiter
        delay=self.delay
        env=self.env

        #for env in env_check_list:
        try:
            env_health = {}
            #instance = instances[env]
            #print(instance)
            #self.url=self.form_url(str(self.domain), str(self.instance_name), str(self.uri_prefix), str(self.uri_suffix))
            #Store url in object
            #self.form_url()

            #print(env_url)
            #env_health[self.format_key("URL")]=self.url
            oh_filter = str(self.overall_health_filter)
            #print(oh_filter)
            
            #Initalize chrome driver
            self.initialize_chrome_driver()

            try:
                wait = WebDriverWait(self.driver, delay)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, oh_filter)))
            except TimeoutException:
                print(env, ": Page Load Timeout")

            koverall,val = self.get_overall_health().split(delimiter)

            #koverall,val = "A","B"
            env_health[self.format_key(koverall)] = val

            #print(oh_filter)
            #for sh_filter in instance["service_filter"]:
            #print(sh_filter)
            sh_filter=self.service_filter
            service_health_dict={}

            for service_health in self.get_services_health():
                k,v = service_health.split(delimiter)
                service_health_dict[self.format_key(k)] = v

            env_health["services"] = service_health_dict
            env_health["instance_details"]=self.get_instance_details()
            self.health_check[env] = env_health


            #get_instance_details(driver)

        except KeyError:
            print("Missing Key")
            print(traceback.format_exc())
            sys.exit()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.health_check)
        #print("--------------------")
        #print(self.health_status)


    #This function returns summarized hc
    def hc_summary(self):
        try:
            self.summary_hc["url"]=self.url
            self.summary_hc["last_hc_time"]=self.health_status["last_hc_time"]
            self.summary_hc["overall_system"]=self.health_status[self.env]["overall_system"]
            self.summary_hc["services"]=True

            for k,v in self.health_status[self.env]["services"].items():
                if v == self.notok_health:
                    self.summary_hc["services"]=False
                    break
       
            if self.summary_hc["services"]:
                self.summary_hc["services"]=self.ok_health
            else:
                self.summary_hc["services"]=self.notok_health
            self.summary_hc["status"]=self.ok_health
        except KeyError:
            self.summary_hc["status"]="KeyError"
                
         


if __name__ == "__main__":
    #(self, env,instance_name, domain="status.salesforce.com", driver_type="chrome", driver_path="/Users/g/drivers/chromedriver"):
    sf=SfHealth("dev", "CSXX")
    sf.perform_health_check()
    print(sf.health_status)
    print()
    sf.hc_summary()
    print(sf.summary_hc)
