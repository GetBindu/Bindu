import tkinter as tk
from tkinter import messagebox
import mysql.connector

def fetch_record_from_mysql(eno):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(host='localhost',user='root',password='sriinformatics',database='demobase')
        cursor = conn.cursor()
        cursor.execute("SELECT eno, ename, esal, egrade FROM myemp WHERE eno = %s", (eno,))
        row = cursor.fetchone()
        conn.close()
        return row
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
        return None

def update_record_in_mysql(old_eno, new_eno, ename, esal, egrade):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(host='localhost',user='root',password='sriinformatics',database='demobase')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE myemp SET eno = %s, ename = %s, esal = %s, egrade = %s WHERE eno = %s",
            (new_eno, ename, esal, egrade, old_eno)
        )
        conn.commit()
        affected_rows = cursor.rowcount
        conn.close()
        return affected_rows
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
        return -1

def fetch_record():
    eno = entry_eno.get()
    if not eno:
        messagebox.showwarning("Input Error", "Please enter an Employee Number.")
        return

    row = fetch_record_from_mysql(eno)
    if row:
        entry_eno_new.delete(0, tk.END)
        entry_eno_new.insert(0, row[0])
        entry_ename.delete(0, tk.END)
        entry_ename.insert(0, row[1])
        entry_esal.delete(0, tk.END)
        entry_esal.insert(0, row[2])
        entry_egrade.delete(0, tk.END)
        entry_egrade.insert(0, row[3])
    else:
        messagebox.showinfo("No Record", f"No record found for Employee Number {eno}.")

def save_update():
    old_eno = entry_eno.get()
    new_eno = entry_eno_new.get()
    ename = entry_ename.get()
    esal = entry_esal.get()
    egrade = entry_egrade.get()

    if not old_eno or not new_eno or not ename or not esal or not egrade:
        messagebox.showwarning("Input Error", "All fields must be filled.")
        return

    affected_rows = update_record_in_mysql(old_eno, new_eno, ename, esal, egrade)
    if affected_rows > 0:
        messagebox.showinfo("Success", f"Record for Employee Number {old_eno} has been updated.")
    elif affected_rows == 0:
        messagebox.showinfo("No Record", f"No record found for Employee Number {old_eno}.")
    else:
        messagebox.showerror("Error", f"An error occurred while trying to update the record.")

# Create the main application window
root = tk.Tk()
root.title("Update Employee Record")

# Add entry and button to input eno
entry_label = tk.Label(root, text="Enter Employee Number to Fetch:")
entry_label.pack(pady=5)

entry_eno = tk.Entry(root)
entry_eno.pack(pady=5)

fetch_button = tk.Button(root, text="Fetch Record", command=fetch_record)
fetch_button.pack(pady=10)

# Add entries for eno, ename, esal, egrade
label_eno_new = tk.Label(root, text="New Employee Number:")
label_eno_new.pack(pady=5)
entry_eno_new = tk.Entry(root)
entry_eno_new.pack(pady=5)

label_ename = tk.Label(root, text="Employee Name:")
label_ename.pack(pady=5)
entry_ename = tk.Entry(root)
entry_ename.pack(pady=5)

label_esal = tk.Label(root, text="Employee Salary:")
label_esal.pack(pady=5)
entry_esal = tk.Entry(root)
entry_esal.pack(pady=5)

label_egrade = tk.Label(root, text="Employee Grade:")
label_egrade.pack(pady=5)
entry_egrade = tk.Entry(root)
entry_egrade.pack(pady=5)

# Add button to save updates
save_button = tk.Button(root, text="Save Update", command=save_update)
save_button.pack(pady=10)

# Run the application
root.mainloop()
