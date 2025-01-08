import pygame
import pytz
import numpy as np
import os, random
from google_drive import *

# Retrieve images from the folder
def getNewImages():
    images = get_images_from_folder(FOLDER_ID)

    files = os.listdir(LOCAL_PATH)
    for image in images:
        if image['name'] not in files:
            download_image(image['id'], image['name'], LOCAL_PATH)
            print(f"downloaded: {image['name']}")

def monthStart(cur:datetime):
    return int(datetime(cur.year, cur.month, 1).strftime('%w'))

class element:
    def __init__(self, n:int) -> None:
        self.n = n
        self.i = 0
        self.assignments = []
        
    def addElement(self, date:dateObject):
        self.assignments.append(date)
        self.i += 1

prevCheck = datetime.now()
prevCheck2 = datetime.now()

def greyscale(surface: pygame.Surface):
    arr = pygame.surfarray.array3d(surface)
    # calulates the avg of the "rgb" values, this reduces the dim by 1
    mean_arr = np.mean(arr, axis=2)
    # restores the dimension from 2 to 3
    mean_arr3d = mean_arr[..., np.newaxis]
    # repeat the avg value obtained before over the axis 2
    new_arr = np.repeat(mean_arr3d[:, :, :], 3, axis=2)
    # return the new surface
    return pygame.surfarray.make_surface(new_arr)

def select_random_background():
    # getNewImages()
    flipped = ["IMG_0589.jpg", "IMG_0474.jpg"]
    files = os.listdir(LOCAL_PATH)
    random_file = random.choice(files)
    print(LOCAL_PATH + random_file)
    bgImg = pygame.image.load(LOCAL_PATH + random_file)
    img_width, img_height = bgImg.get_size()
    img_aspect_ratio = img_width / img_height
    display_aspect_ratio = fullWidth / height
    if img_aspect_ratio <= display_aspect_ratio:
        # Scale the image to fit the width of the display area
        scaled_width = fullWidth
        scaled_height = int(fullWidth / img_aspect_ratio)
    else:
        # Scale the image to fit the height of the display area
        scaled_height = height
        scaled_width = int(height * img_aspect_ratio)
        
    bgImg = pygame.transform.scale(bgImg, (scaled_width, scaled_height))
    # if random_file in flipped:
        # bgImg = pygame.transform.rotate(bgImg, 180)
        # bgImg = pygame.transform.flip(bgImg, True, True)

    # Calculate the position to center the image on the screen
    center_x = (fullWidth - scaled_width) // 2
    center_y = (height - scaled_height) // 2
    return bgImg, center_x, center_y

pygame.init()
height = 480
fullWidth = 800
width = (fullWidth-150)//7*7
todoSize = fullWidth-width
clock = pygame.time.Clock()
running = True
lastClick = datetime.now()
viewGrading = True
nextTime = None
previousHour = datetime.now().hour

curPerson = "Noah"

if runningOnPi:
    screen = pygame.display.set_mode((width+todoSize, height), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((width+todoSize, height))

dates = []
daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
dayLengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
curDay = datetime.utcnow()
result = 0
titleSize = 60
borderColor = (150, 125, 220)
titleFontSize = 50
textFontSize = 14
todoFontSize = 18
titleFont = 'microsoftsansserif'
textFont = 'liberationserif'
font = pygame.font.SysFont(titleFont, titleFontSize)
tempText = font.render("September" + " " + str(curDay.year), True, (0, 0, 0))
font = pygame.font.SysFont(textFont, textFontSize)
tempTextRect = tempText.get_rect()
maxWidth = tempTextRect.width

bgFileName = "background.jpeg"

luminocity = 160

checkDate = None
checkDateTimer = datetime.now()

calStartDate = None
calEndDate = None

leftClick = None
rightClick = None
gradingTick = None
n = int(((height-titleSize)/6)//(textFontSize+2))

rename = {}
rename[2165800] = 'TA: C291'
rename[2165732] = 'Economic Security'
rename[2165707] = 'Applied Algorithms'

CALENDAR = [[None for i in range(7)] for i in range(6)]
ASSIGNMENTS = [[element(n) for i in range(7)] for i in range(6)]

todoList = []

# bgImg = greyscale(bgImg)
bgImg, center_x, center_y = select_random_background()

def isLeapYear(year):
    return year % 4 == 0 and year % 100 != 0 or year % 400 == 0

def prevMonth(date):
    if date.month == 1:
        curDay = datetime(date.year-1, 12, 1)
    else:
        curDay = datetime(date.year, date.month-1, 1)
    return curDay
        
def nextMonth(date):
    if date.month == 12:
        curDay = datetime(date.year+1, 1, 1)
    else:
        curDay = datetime(date.year, date.month+1, 1)
    return curDay

def clearAssignments():
    global ASSIGNMENTS
    for row in range(6):
        for col in range(7):
            ASSIGNMENTS[row][col].assignments = []
            ASSIGNMENTS[row][col].i = 0   
            
def switchPerson():
    global dates, nextTime, curPerson
    if curPerson == "Noah":
        curPerson = "Kaitlyn"
    elif curPerson == "Kaitlyn":
        curPerson = "Noah" 
    dates = checkUpdate(curPerson)
    updateCalendar(curDay)
    updateAssignments()
    
def findNextTime():
    global nextTime, dates
    nextTime = None
    for i in dates:
        if nextTime == None and i.assignmentID not in ignore:
            if (i.type == 'event' or i.type == 'countdown') and i.startDate >= datetime.now(tz=pytz.timezone('US/Eastern')):
                nextTime = (i.assignmentName, i.startDate)
            elif i.dueDate >= datetime.now(tz=pytz.timezone('US/Eastern')):
                nextTime = (i.assignmentName, i.dueDate)
        elif i.assignmentID not in ignore:
            if (i.type == 'event' or i.type == 'countdown') and i.startDate >= datetime.now(tz=pytz.timezone('US/Eastern')) and i.startDate <= nextTime[1]:
                nextTime = (i.assignmentName, i.startDate)
            elif i.dueDate >= datetime.now(tz=pytz.timezone('US/Eastern')) and i.dueDate <= nextTime[1]:
                nextTime = (i.assignmentName, i.dueDate)
        

def updateAssignments():
    clearAssignments()
    for date in dates:
        curDate = date.dueDate - timedelta(seconds=1)
        if date.assignmentID in ignore or (viewGrading and date.type == 'grading'):
            continue
        if curDate >= calStartDate and curDate <= calEndDate:
            inPrevMonth = curDate.month == (curDay.month + 10) % 12 + 1
            inCurMonth = curDate.month == curDay.month
            inNextMonth = curDate.month == curDay.month % 12 + 1
            curMonth = -1
            flag = False
            for row in range(6):
                for col in range(7):
                    if curMonth == -1 and CALENDAR[row][col][0] == 1:
                        curMonth = 0
                    elif curMonth == 0 and CALENDAR[row][col][0] == 1:
                        curMonth = 1
                    if (inPrevMonth and curMonth == -1) or (inCurMonth and curMonth == 0) or (inNextMonth and curMonth == 1):
                        if curDate.day == CALENDAR[row][col][0]:
                            ASSIGNMENTS[row][col].addElement(date)
                            flag = True
                            break
                if flag:
                    break

def updateCalendar(startingDate):
    global CALENDAR, calStartDate, calEndDate
    p = prevMonth(startingDate)
    a = nextMonth(startingDate)
    prevMonthDate = dayLengths[p.month-1]
    curMonthDays = dayLengths[curDay.month-1]
    if p.month == 2 and isLeapYear(p.year):
        prevMonthDate += 1
    if curDay.month == 2 and isLeapYear(curDay.year):
        curMonthDays += 1
    c = monthStart(startingDate)
    if c == 0:
        calStartDate = datetime(startingDate.year, startingDate.month, 1, tzinfo=pytz.UTC)
    else:
        calStartDate = datetime(p.year, p.month, prevMonthDate-c+1, tzinfo=pytz.UTC)
    calEndDate = datetime(a.year, a.month, 42-(curMonthDays+c), 23, 59, 59, 999999, tzinfo=pytz.UTC)
    row = 0
    for i in range(c):
        CALENDAR[row+i//7][i%7] = (prevMonthDate-c+i+1, False)
    for i in range(c, curMonthDays+c):
        CALENDAR[row+i//7][i%7] = (i-c+1, True)
    for i in range(curMonthDays+c, 42):
        CALENDAR[row+i//7][i%7] = (i-(curMonthDays+c)+1, False)
    
dates = checkUpdate(curPerson)
findNextTime()
updateCalendar(curDay)
updateAssignments()

prevClick = None

while running:
    realDay = datetime.now()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.KEYDOWN and pygame.key.get_pressed()[pygame.K_s]:
            switchPerson()
            print(curPerson)
            
        if event.type == pygame.KEYDOWN and pygame.key.get_pressed()[pygame.K_RIGHT]:
            bgImg, center_x, center_y = select_random_background()                
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            prevClick = (datetime.utcnow(), pygame.mouse.get_pos())
            
        if event.type == pygame.MOUSEBUTTONUP:
            lastClick = datetime.utcnow()
            if leftClick == None:
                continue
            pos = pygame.mouse.get_pos()
            if checkDate:
                continue
            if leftClick.collidepoint(pos):
                curDay = prevMonth(curDay)
                updateCalendar(curDay)
            elif rightClick.collidepoint(pos):
                curDay = nextMonth(curDay)
                updateCalendar(curDay)
            elif gradingTick.collidepoint(pos):
                viewGrading = not viewGrading
            elif prevClick is not None and lastClick - prevClick[0] >= timedelta(seconds=2):
                for i in todoList:
                    if i[1].collidepoint(pos):
                        ignore.append(i[0].assignmentID)
            else:
                for i in range(7):
                    for j in range(6):
                        box = pygame.Rect(width//7*i, titleSize+(height-titleSize)//6*j, width//7, (height-titleSize)//6)
                        if box.collidepoint(pos):
                            checkDateTimer = datetime.now() + timedelta(seconds=10)
                            checkDate = (j, i)
            if pos[0] < 5 and pos[1] < 5:
                running = False   
            updateAssignments()
    
        
    screen.fill((255, 255, 255))
    if (datetime.now() - lastClick).total_seconds() >= 10:
        pygame.mouse.set_pos(width, height)
    if datetime.now().second == 0 and (datetime.now() - prevCheck).total_seconds() >= 60:
        prevCheck = datetime.now()
        dates = checkUpdate(curPerson)
        updateAssignments()
        synchronize_images()
    if datetime.now().second == 0 and (datetime.now() - prevCheck2).total_seconds() >= 5:
        prevCheck2 = datetime.now()
        findNextTime()
    if datetime.now().hour != previousHour:
        bgImg, center_x, center_y = select_random_background()
        previousHour = datetime.now().hour
    
    if checkDate:
        if datetime.now() >= checkDateTimer:
            checkDate = None
            
    screen.blit(bgImg, (center_x, center_y))
    
    s = pygame.Surface((fullWidth,titleSize))  # the size of your rect
    s.set_alpha(luminocity)                # alpha level
    s.fill((255,255,255))           # this fills the entire surface
    screen.blit(s, (0,0))    # (0,0) are the top-left coordinates
    
    # Print the title
    font = pygame.font.SysFont(titleFont, titleFontSize)
    text = font.render(months[curDay.month-1] + " " + str(curDay.year), True, (0, 0, 0))
    textRect = text.get_rect()
    textRect.center = (width // 2, titleSize // 2)
    screen.blit(text, textRect)
    font = pygame.font.SysFont(titleFont, 30)
    # timeLeft = str(datetime.utcfromtimestamp(1714175400)-datetime.utcnow())
    # timeLeft = timeLeft.split('.')[0].split(', ')
    # text = font.render(timeLeft[0], True, (0, 0, 0))
    # textRect3 = text.get_rect()
    # textRect3.center = (width // 2, titleSize // 2)
    # textRect3.left = 0
    # textRect3.top = textRect3.top-15
    # screen.blit(text, textRect3)
    # text = font.render(timeLeft[1], True, (0, 0, 0))
    # textRect3 = text.get_rect()
    # textRect3.center = (width // 2, titleSize // 2)
    # textRect3.left = 0
    # textRect3.top = textRect3.top+15
    # screen.blit(text, textRect3)
    words = str(datetime.now(tz=pytz.timezone('US/Eastern'))).split()
    text = font.render(words[0], True, (0, 0, 0))
    textRect2 = text.get_rect()
    textRect2.center = (width // 2, titleSize // 2)
    textRect2.left = 0
    textRect2.top = textRect2.top-15
    screen.blit(text, textRect2)
    words[1] = words[1].split(":")
    words[1][2] = words[1][2].split(".")[0]
    period = " am"
    if int(words[1][0]) >= 12:
        period = " pm"
    words[1][0] = str(((int(words[1][0])+11)%12)+1)
    text = font.render(words[1][0]+":"+words[1][1]+":"+words[1][2]+period, True, (0, 0, 0))
    textRect2 = text.get_rect()
    textRect2.center = (width // 2, titleSize // 2)
    textRect2.left = 0
    textRect2.top = textRect2.top+15
    screen.blit(text, textRect2)
    # # show the time until my next class
    if nextTime is not None:
        timeUntilNextEvent = str(nextTime[1]-datetime.now(tz=pytz.timezone('US/Eastern'))).split('.')[0]
        text = font.render(timeUntilNextEvent, True, (0, 0, 0))
        textRect5 = text.get_rect()
        textRect5.center = (width // 2, titleSize // 2)
        textRect5.left = width
        textRect5.top = textRect5.top+15
        screen.blit(text, textRect5)
        text = font.render(nextTime[0], True, (0, 0, 0))
        textRect5 = text.get_rect()
        textRect5.center = (width // 2, titleSize // 2)
        textRect5.left = width
        textRect5.top = textRect5.top-15
        screen.blit(text, textRect5)
    # print(nextTime-datetime.now())
    
    # print the left and right arrows
    font = pygame.font.SysFont(textFont, textFontSize)
    leftClick = pygame.Rect(width//2-maxWidth//2-43.3-20, titleSize//2-25, 43.3, 50)
    rightClick = pygame.Rect(width//2+maxWidth//2+20, titleSize//2-25, 43.3, 50)
    gradingTick = pygame.Rect(fullWidth-200, titleSize//2-25, 200, 50)
    
    pygame.draw.polygon(screen, (128,0,128), [(width//2+maxWidth//2+20, titleSize//2-25), (width//2+maxWidth//2+20, titleSize//2+25), (width//2+43.3+maxWidth//2+20, titleSize//2)])
    pygame.draw.polygon(screen, (128,0,128), [(width//2-maxWidth//2-20, titleSize//2-25), (width//2-maxWidth//2-20, titleSize//2+25), (width//2-43.3-maxWidth//2-20, titleSize//2)])
    
    if checkDate:
        s = pygame.Surface((width,height-titleSize))  # the size of your rect
        s.set_alpha(luminocity)                # alpha level
        s.fill((255,255,255))           # this fills the entire surface
        screen.blit(s, (0,titleSize))    # (0,0) are the top-left coordinates
        for i in range(ASSIGNMENTS[checkDate[0]][checkDate[1]].i):
            textRect = pygame.Rect(2+20, titleSize+20*i+textFontSize+2+textFontSize*i, width-2, 20)
            text = ASSIGNMENTS[checkDate[0]][checkDate[1]].assignments[i].assignmentName + " "
            if ASSIGNMENTS[checkDate[0]][checkDate[1]].assignments[i].dueDate - ASSIGNMENTS[checkDate[0]][checkDate[1]].assignments[i].startDate >= timedelta(days=1)-timedelta(seconds=1):
                text += "all day"
            else:
                start = str(ASSIGNMENTS[checkDate[0]][checkDate[1]].assignments[i].startDate).split()[1]
                end = str(ASSIGNMENTS[checkDate[0]][checkDate[1]].assignments[i].dueDate).split()[1]
                if int(start[0:2]) >= 0 and int(start[0:2]) < 12:
                    if (int(start[0:2]) == 0):
                        start = '12' + start[2:]
                    if (int(start[3:5]) == 0):
                        start = start[:2]
                    elif (int(start[6:8]) == 0):
                        start = start[:5]
                    start += ' am'
                else:
                    if (int(start[0:2]) > 12):
                        start = str((int(start[0:2])%12)//10) + str((int(start[0:2])%12)%10) + start[2:]
                    if (int(start[3:5]) == 0):
                        start = start[:2]
                    elif (int(start[6:8]) == 0):
                        start = start[:5]
                    start += ' pm'
                if int(end[0:2]) >= 0 and int(end[0:2]) < 12:
                    if (int(end[0:2]) == 0):
                        end = '12' + end[2:]
                    if (int(end[3:5]) == 0):
                        end = end[:2]
                    elif (int(end[6:8]) == 0):
                        end = end[:5]
                    end += ' am'
                else:
                    if (int(end[0:2]) > 12):
                        end = str((int(end[0:2])%12)//10) + str((int(end[0:2])%12)%10) + end[2:]
                    if (int(end[3:5]) == 0):
                        end = end[:2]
                    elif (int(end[6:8]) == 0):
                        end = end[:5]
                    end += ' pm'
                text += start + " - " + end
            # print(text)
            screen.blit(font.render(text, True, (0, 0, 0)), textRect)
    else:
        # print each element on the calendar
        for row in range(6):
            for col in range(7):
                cropRect = pygame.Rect(width//7*col, titleSize+(height-titleSize)//6*row, width//7, (height-titleSize)//6)
                # screen.blit(bgImg, cropRect, cropRect)
                # pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(width//7*col, titleSize+(height-titleSize)//6*row, width//7, (height-titleSize)//6))
                s = pygame.Surface((width//7,(height-titleSize)//6))  # the size of your rect
                s.set_alpha(luminocity)                # alpha level
                s.fill((255,255,255))           # this fills the entire surface
                screen.blit(s, (width//7*col,titleSize+(height-titleSize)//6*row))    # (0,0) are the top-left coordinates
                if CALENDAR[row][col][1] == True:
                    if curDay.month == realDay.month and curDay.year == realDay.year and CALENDAR[row][col][0] == realDay.day:
                        # pygame.draw.rect(screen, (220, 220, 220), pygame.Rect(width//7*col, titleSize+(height-titleSize)//6*row, width//7, (height-titleSize)//6))
                        s = pygame.Surface((width//7,(height-titleSize)//6))  # the size of your rect
                        s.set_alpha(120)                # alpha level
                        s.fill((255,255,255))           # this fills the entire surface
                        screen.blit(s, (width//7*col,titleSize+(height-titleSize)//6*row))    # (0,0) are the top-left coordinates
                        screen.blit(font.render(str(CALENDAR[row][col][0]), True, (255, 0, 0), None), pygame.Rect(width/7*col+2, titleSize+(height-titleSize)/6*row+2, width//7, 20))
                    else:
                        screen.blit(font.render(str(CALENDAR[row][col][0]), True, (0, 0, 0), None), pygame.Rect(width/7*col+2, titleSize+(height-titleSize)/6*row+2, width//7, 20))
                else:
                    screen.blit(font.render(str(CALENDAR[row][col][0]), True, (50, 50, 50), None), pygame.Rect(width/7*col+2, titleSize+(height-titleSize)/6*row+2, width//7, 20))
                for i in range(ASSIGNMENTS[row][col].i):
                    text_rect = pygame.Rect(2+width/7*col, titleSize+(height-titleSize)/6*row+textFontSize+2+textFontSize*i, width//7, 20)
                    if ASSIGNMENTS[row][col].assignments[i].type == 'event':
                        text_surface = font.render(str(ASSIGNMENTS[row][col].assignments[i].assignmentName), True, (0, 0, 0))
                    else:
                        text_surface = font.render(str(ASSIGNMENTS[row][col].assignments[i].assignmentName), True, (180, 50, 50))
                    source_rect = pygame.Rect(0, 0, min(text_surface.get_width(), text_rect.width), min(text_surface.get_height(), text_rect.height))
                    screen.blit(text_surface, text_rect, area=source_rect)
                pygame.draw.rect(screen, borderColor, pygame.Rect(width//7*col, titleSize+(height-titleSize)//6*row, width//7, (height-titleSize)//6), 2)
    
    
    # pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(width//7*7, titleSize, todoSize, height-titleSize))
    cropRect = pygame.Rect(width//7*7, titleSize, todoSize, height-titleSize)
    # screen.blit(bgImg, cropRect, cropRect)
    s = pygame.Surface((todoSize,height-titleSize))  # the size of your rect
    s.set_alpha(luminocity)                # alpha level
    s.fill((255,255,255))           # this fills the entire surface
    screen.blit(s, (width//7*7,titleSize))    # (0,0) are the top-left coordinates
    font = pygame.font.SysFont(textFont, todoFontSize)
    
    i = 0
    actualCount = 0
    todoList = []
    while i < len(dates):
        while len(dates) > i and (dates[i].assignmentID in ignore or dates[i].type == 'exam' or dates[i].type == 'event' or (viewGrading and dates[i].type == 'grading') or (dates[i].type == 'countdown' and (dates[i].startDate - datetime.now(tz=pytz.timezone('US/Eastern'))).total_seconds() < 0)):
            i += 1
        if len(dates) <= i:
            break
        else:
            color = (0, 0, 0)
            # if dates[i].type == 'countup':
            #     color = (180, 50, 50)
            if dates[i].classID in rename:
                screen.blit(font.render(str(rename[dates[i].classID]), True, color), pygame.Rect(width+5, titleSize+actualCount*70, todoSize-5, 20))
            else:
                screen.blit(font.render(str(dates[i].className), True, color), pygame.Rect(width+5, titleSize+actualCount*70, todoSize-5, 20))
            screen.blit(font.render(str(dates[i].assignmentName), True, color), pygame.Rect(width+5, titleSize+actualCount*70+20, todoSize-5, 20))
            if dates[i].type == 'countdown':
                seconds = (dates[i].startDate - datetime.now(tz=pytz.timezone('US/Eastern'))).total_seconds()
                if seconds < 0:
                    seconds = (dates[i].dueDate - datetime.now(tz=pytz.timezone('US/Eastern'))).total_seconds()
            elif dates[i].type == 'countup':
                seconds = (dates[i].dueDate - datetime.now(tz=pytz.timezone('US/Eastern'))).total_seconds()
            else:
                seconds = (dates[i].dueDate - datetime.now(tz=pytz.timezone('US/Eastern'))).total_seconds()
            days = int(seconds // 60 // 60 // 24)
            hours = int(seconds // 60 // 60 % 24)
            minutes = int(seconds // 60 % 60)
            seconds = int(seconds % 60)
            screen.blit(font.render((str(days) + " days, " + str(hours) + ":" + f'{minutes:02d}' + ":" + f'{seconds:02d}'), True, color), pygame.Rect(width+5, titleSize+actualCount*70+40, todoSize-5, 20))
            tempThing = dates[i]
            if len(todoList) != 0:
                todoList.append((tempThing, pygame.Rect(width+5, todoList[-1][1][1]+70, todoSize-5, 60)))
            else:
                todoList.append((tempThing, pygame.Rect(width+5, titleSize, todoSize-5, 60)))
            actualCount += 1
        i += 1

    pygame.display.flip()

    clock.tick(60)

pygame.quit()