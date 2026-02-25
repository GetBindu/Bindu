import mysql.connector
from tkinter import *
root= Tk()
root.geometry("500x300")
my_connect = mysql.connector.connect(host="localhost",user="root",passwd="12345",database="demobase")
my_conn = my_connect.cursor()
my_conn.execute("SELECT * FROM myemp LIMIT 10")
for i, row in enumerate(my_conn, start=1):  # start=1 to begin at row 1
    for j, value in enumerate(row):
        e = Entry(width=15, fg='blue')
        e.grid(row=i, column=j)
        e.insert(END, str(value))
mainloop()
