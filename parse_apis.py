import requests, json
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pytz
from googleapiclient.errors import HttpError
import socket

runningOnPi = True
ignore = []

# Load credentials from JSON file
credentials_file = '/home/noah/Documents/Calendar/calendarlink-405200-1929a51bbf80.json'
try:
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=['https://www.googleapis.com/auth/calendar'])
except:
    runningOnPi = False
    credentials_file = 'calendarlink-405200-1929a51bbf80.json'
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=['https://www.googleapis.com/auth/calendar'])
    

# Build the service
service = build('calendar', 'v3', credentials=credentials)

class dateObject:
    def __init__(self, className:str, assignmentName:str, startDate:datetime, dueDate:datetime, classID:int, assignmentID:int, type:str) -> None:
        self.className = className
        self.assignmentName = assignmentName
        self.startDate = startDate
        self.dueDate = dueDate
        self.classID = classID
        self.assignmentID = assignmentID
        self.type = type
    

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
    # return utc_dt

def strToDateTime(a:str, convert:bool) -> datetime:
    result = None
    if len(a) == 8:
        today_date = datetime.now().date()
        result = datetime.combine(today_date, datetime.strptime(a, '%H:%M:%S').time())
    elif len(a) == 10:
        result = datetime.strptime(a, '%Y-%m-%d')
    elif len(a) == 25:
        b = a[0:19]+'Z'
        # c = a[0:10]+'T'+a[20:25]+':00Z'
        result = datetime.strptime(b, '%Y-%m-%dT%H:%M:%SZ')
        # datetime.strptime(c, '%Y-%m-%dT%H:%M:%SZ')
    else:
        result = datetime.strptime(a, '%Y-%m-%dT%H:%M:%SZ')
    if convert:
        return utc_to_local(result)
    # x = []
    # for i in result:
    #     x.append(i.replace(tzinfo=pytz.timezone('EST')))
    return result

def fillNextDays(x:datetime):
    days = [None for i in range(7)]
    start = datetime.now().isoweekday() % 7
    curDay = datetime.now().replace(hour=x.hour, minute=x.minute, second=x.second)
    if datetime.now() > x:
        start = (start + 1) % 7
        curDay += timedelta(days=1)
    for i in range(7):
        days[(i+start)%7] = curDay
        curDay += timedelta(days=1)
    return days

def prettyPrint(data):
    print(json.dumps(data, indent=2))
    
def listOfDays(a:datetime, b:datetime):
    date_list = []
    current_date = a
    if current_date < b:
        builtDay = [None, None]
        builtDay[0] = current_date
        current_date = pytz.timezone('US/Eastern').localize(datetime(a.year, a.month, a.day))
        current_date += timedelta(days=1)
        if current_date <= b:
            builtDay[1] = current_date-timedelta(seconds=1)
        else:
            builtDay[1] = b
        date_list.append(builtDay)
    while current_date < b:
        builtDay = [None, None]
        builtDay[0] = current_date
        current_date += timedelta(days=1)
        if current_date <= b:
            builtDay[1] = current_date-timedelta(seconds=1)
        else:
            builtDay[1] = b
        date_list.append(builtDay)
    return date_list  
    
def checkUpdate(person:str) -> list[dateObject]:
    result = []
    calendar_id = 'kaitlynmason11@gmail.com'  # Use 'primary' for the primary calendar
    one_year_ago = datetime.now() - timedelta(days=365)
    formatted_one_year_ago = one_year_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
    events_result = service.events().list(calendarId=calendar_id, timeMin=formatted_one_year_ago, maxResults=1000, singleEvents=True, orderBy='startTime').execute()
    if events_result == None or len(events_result) == 0:
        return result
    events = events_result.get('items', [])
    seen = set()
    oneCountEvents = set()
    for event in events:
        start = strToDateTime(event['start'].get('dateTime', event['start'].get('date')), False)
        start = pytz.timezone('US/Eastern').localize(start)
        end = strToDateTime(event['end'].get('dateTime', event['end'].get('date')), False)
        end = pytz.timezone('US/Eastern').localize(end)
        if event['summary'] == 'Last day of classes [pre-finals]':
            pass
        length = listOfDays(start, end)
        try:
            if 'countdown' in event["description"] or 'Countdown' in event["description"]:
                result.append(dateObject(None, event["summary"], start, end, None, event['id'], 'countdown'))
            if 'onecount' in event["description"].lower() and event["summary"] not in seen:
                if end > datetime.now(tz=pytz.timezone('US/Eastern')):
                    oneCountEvents.add(event['id'])
                    seen.add(event["summary"])
                    result.append(dateObject(None, event["summary"], start, end, None, event['id'], 'countdown'))
            if 'countup' in event["description"] or 'Countup' in event["description"] or 'CountUp' in event["description"]:
                result.append(dateObject(None, event["summary"], start, end, None, event['id'], 'countup'))
        except:
            pass
        finally:
            for i in length:
                try:
                    if 'countdown' not in event["description"] and 'Countdown' not in event["description"] and event['id'] not in oneCountEvents:
                        result.append(dateObject(None, event["summary"], i[0], i[1], None, event['id'], 'event'))
                except:
                    result.append(dateObject(None, event["summary"], i[0], i[1], None, event['id'], 'event'))
    return result
    # else:
    #     # Print an error message if the request was not successful
    #     print(f"Error: {response.status_code} - {response.text}")
    