import pandas as pd

class data_OULA:
    def __init__(self, name):
        self.name = name

    def setData(self, assessments, courses,studentAssessment, studentInfo, studentRegistration, studentVle, vle, users, teachers):
        self.assessments = assessments
        self.courses = courses
        self.studentAssessment = studentAssessment
        self.studentInfo = studentInfo
        self.studentRegistration = studentRegistration
        self.studentVle = studentVle
        self.vle = vle
        self.users = users
        self.teachers = teachers

    def getUsers(self):
        return self.users

    def getStudentRegistation(self):
        return self.studentRegistration

    def getTeachers(self):
        return self.teachers

    def getStudentsInfo(self):
        return self.studentInfo

    def getAssessments(self):
        return self.assessments

    def getStudentAssessments(self):
        return self.studentAssessment

    def getStudentVle(self):
        return self.studentVle