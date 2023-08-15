import pandas as pd

studentRegistration = pd.read_csv("DB/studentRegistration.csv")

studentReg = studentRegistration[studentRegistration["id_student"] == 277880]

x = []

for st in studentReg:
    print(st["code_presentation"])
# print(studentReg)