import easygui
from easygui import buttonbox
import PIL.Image
import cv2, PySimpleGUI as sg
from PIL import Image
from PIL.Image import Resampling
from sqlite3 import connect


# Replace username with your own A2 Hosting account username:

conn = connect('C:/Temp/deepface.db')
curs = conn.cursor()

curs.execute("Select * From Employees where ID = 4")
for id,firstname,lastname,age,job,employee_image in curs.fetchall():
    print(firstname, lastname, age, job, employee_image)
conn.close()

basewidth = 300
img = Image.open(employee_image)
wpercent = (basewidth/float(img.size[0]))
hsize = int((float(img.size[1])*float(wpercent)))
img = img.resize((basewidth,hsize), Resampling.LANCZOS)
img.save(employee_image)


title = "Employee Details"
msg = "Name: " + firstname + " " + lastname+"\nAge: " + str(age) + "\nJob: " + job
choices = ["OK"]

reply = buttonbox(msg=msg, title=title, choices=(choices), image=employee_image)

# easygui.msgbox("Name: " + firstname + " " + lastname+"\n" +
#                 "Age: " + str(age) + "\n" +
#                 "Job: " + job + "\n" +
#                 image=img, title="Employee Details")