import time
import numpy as np
#import datetime
import swigibpy as swig


MEANINGLESS_ID=503

def return_IB_connection_info():
    """
    Returns the tuple host, port, clientID required by eConnect
    """
    host =''
    port = 7496
    clientid = 183   
    return (host, port, clientid)


class IBWrapper(swig.EWrapperVerbose):
    """
    Callback object passed to TWS, these functions will be called directly by the TWS or Gateway.
    """
    ## We need these but don't use them
    def nextValidId(self, orderId):
        pass
   
    def managedAccounts(self, openOrderEnd):
        pass

    ## error handling
    def init_error(self):
        setattr(self, "flag_iserror", False)
        setattr(self, "error_msg", "")

    def error(self, id, errorCode, errorString):
        """
        error handling, simple for now
       
        Here are some typical IB errors
        INFO: 2107, 2106
        WARNING 326 - can't connect as already connected
        CRITICAL: 502, 504 can't connect to TWS.
            200 no security definition found
            162 no trades
        """
        ## Any errors not on this list we just treat as information
        ERRORS_TO_TRIGGER=[201, 103, 502, 504, 509, 200, 162, 420, 2105, 1100, 478, 201, 399]
       
        if errorCode in ERRORS_TO_TRIGGER:
            errormsg="IB error id %d errorcode %d string %s" %(id, errorCode, errorString)
            print errormsg
            setattr(self, "flag_iserror", True)
            setattr(self, "error_msg", True)


    def init_tickdata(self, TickerId):
        if "data_tickdata" not in dir(self):
            tickdict=dict()
        else:
            tickdict=self.data_tickdata

        tickdict[TickerId]=[np.nan]*4
        setattr(self, "data_tickdata", tickdict)


    def tickString(self, TickerId, field, value):
        marketdata=self.data_tickdata[TickerId]
        tickType=field
        if int(tickType)==0:              ## bid size
            marketdata[0]=int(value)
        elif int(tickType)==3:            ## ask size
            marketdata[1]=int(value)
        elif int(tickType)==1:            ## bid
            marketdata[0][2]=float(value)
        elif int(tickType)==2:            ## ask
            marketdata[0][3]=float(value)
        

    def tickGeneric(self, TickerId, tickType, value):
        marketdata=self.data_tickdata[TickerId]
        if int(tickType)==0:              ## bid size
            marketdata[0]=int(value)
        elif int(tickType)==3:            ## ask size
            marketdata[1]=int(value)
        elif int(tickType)==1:            ## bid
            marketdata[2]=float(value)
        elif int(tickType)==2:            ## ask
            marketdata[3]=float(value)
           

    def tickSize(self, TickerId, tickType, size):
        marketdata=self.data_tickdata[TickerId]
        if int(tickType)==0:              ## bid size
            marketdata[0]=int(size)
        elif int(tickType)==3:            ## ask size
            marketdata[1]=int(size)
   

    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        marketdata=self.data_tickdata[TickerId]        
        if int(tickType)==1:              ## bid
            marketdata[2]=float(price)
        elif int(tickType)==2:            ## ask
            marketdata[3]=float(price)

        
    def tickSnapshotEnd(self, tickerId):        
        print "No longer want to get %d" % tickerId

class IBclient(object):
    """
    Client class
        self.wrapper = IBWrapper()
        self.client = IBclient(self.wrapper)
    """
    def __init__(self, wrapper):
        self.wrapper = wrapper
        tws = swig.EPosixClientSocket(self.wrapper)
        self.tws = tws
        (host, port, clientid)=return_IB_connection_info()
        tws.eConnect(host, port, clientid);  time.sleep(1)

        
    def get_IB_market_data(self, ibcontract, seconds=30, tickerid=MEANINGLESS_ID):
        """
        Returns granular market data
        
        Returns a tuple (bid price, bid size, ask price, ask size)
        
        """
        self.tickerid = tickerid
        self.ibcontract = ibcontract
        self.wrapper.init_tickdata(tickerid)
        self.wrapper.init_error()
        # Request a market data stream 
        self.tws.reqMktData( tickerid, self.ibcontract, '', True, None)

        start_time=time.time()
        finished = False
        iserror = False
        while not finished and not iserror:
            iserror = self.wrapper.flag_iserror
            if (time.time() - start_time) > seconds:
                finished = True
            pass
        self.tws.cancelMktData(tickerid)
        
        marketdata = self.wrapper.data_tickdata[tickerid]
        ## marketdata should now contain some interesting information
        ## Note in this implementation we overwrite the contents with each tick; we could keep them
              
        if iserror:
            print "Error: "+self.wrapper.error_msg
            print "Failed to get any prices with marketdata"
        
        return marketdata
    
wrapper = IBWrapper()
client = IBclient(wrapper)

end_date = '20160301'
end_time = '16:00:00'
bar_size = '30 mins'
duration = '1 M'
rth = True
contract = swig.Contract()
contract.symbol = 'ES'
contract.secType = 'FUT'
contract.exchange = 'GLOBEX'
contract.currency = 'USD'
contract.expiry = '201606'
#today = datetime.today()

ticks = client.get_IB_market_data(contract, seconds=30, tickerid=MEANINGLESS_ID)
print ticks
time.sleep(5)

client.tws.reqCurrentTime()
client.tws.eDisconnect()