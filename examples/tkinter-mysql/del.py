import mysql.connector
from tkinter import *
from tkinter import messagebox

conn = mysql.connector.connect(host="localhost",user="root",passwd="sriinformatics",database="demobase")
cursor = conn.cursor()
root = Tk()
root.geometry("400x200")

Label(text='Enter Employee Number to Delete:', width=30).grid(row=1, column=1)

entry = Text( height=1, width=4, bg='yellow')
entry.grid(row=1, column=2)

def delete_record():
    eno = entry.get('1.0', 'end').strip()
    val = int(eno)
    cursor.execute("DELETE FROM myemp WHERE eno = %s", (val,))
    conn.commit()  
    if cursor.rowcount > 0:
            messagebox.showinfo("Success","Employee record deleted successfully.")
    else:
            messagebox.showinfo("Error","Employee not found.")
    

# Delete Button
Button(root, text='Delete Record', width=15, bg='red', command=delete_record).grid(row=1, column=4)

# Start Tkinter main loop
root.mainloop()
