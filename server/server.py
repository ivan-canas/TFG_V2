from re import X
from flask import Flask
from data import data_OULA
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.tree import plot_tree
# import matplotlib.pyplot as plt

app = Flask(__name__)
data = data_OULA("test")

@app.route('/User/<user_name>/<user_password>', methods=['GET'])
def checkUser(user_name,user_password):
    users = data.getUsers()
    isUser = users[(users["user_name"] == user_name)]
    isUser = isUser[isUser["password"] == user_password] #check passwd type
    
    if isUser.shape[0] == 1:
        return({"log":True, "user_type":isUser["type"].item(), "id_user":isUser["id_user"].item()})
    else:
        return({"log":False})

@app.route('/student/<user_id>', methods=['GET'])
def getStudentCourses(user_id):
    users = data.getUsers()
    user = users[users["id_user"] == int(user_id)]
    student_id = user["id_type"].item()
    studentReg = data.getStudentRegistation()
    studentReg = studentReg[studentReg["id_student"] == student_id]
    courses = []
    for course,subject in zip(studentReg["code_presentation"],studentReg["code_module"]):
        courses.append({"value":"-".join([course,subject]), "label": "-".join([course,subject])})
    
    return({"course": courses})
        

@app.route('/teacher/<user_id>', methods=['GET'])
def getTeacherCourses(user_id):
    users = data.getUsers()
    user = users[users["id_user"] == int(user_id)]
    teacher_id = user["id_type"].item()
    teacher = data.getTeachers()
    teacher = teacher[teacher["id_teacher"] == teacher_id]
    courses = []
    for course,subject in zip(teacher["code_presentation"],teacher["code_module"]):
        courses.append({"value":"-".join([course,subject]), "label": "-".join([course,subject])})
    
    return({"course": courses})

@app.route("/student/data/<user_id>/<course>/<subject>/<time>")
def getStudentCourseData(user_id,course,subject,time):
    users = data.getUsers()
    user = users[users["id_user"] == int(user_id)]
    students = data.getStudentsInfo()
    student = students[students["id_student"]==int(user["id_type"])]
    student_unique = student[student["code_presentation"] == course]
    student_unique = student_unique[student_unique["code_module"] == subject]
    std_info = setStudentsInfo(student_unique,course, subject, time)
    return std_info

@app.route("/teacher/data/<course>/<subject>/<time>")
def getCourseData(course,subject,time):
    #get students from that course and subject
    courseReg = data.getStudentRegistation()
    courseReg = courseReg[courseReg["code_presentation"] == course ]
    courseReg = courseReg[courseReg["code_module"] == subject ]
    max_registered = len(courseReg)
    #fill unregistration for the ones that passed
    courseReg = courseReg.fillna(1000)
    #filter by actual students
    courseReg = courseReg[courseReg["date_unregistration"] >= int(time)]
    #dont get students duplicated
    students_ids = []
    for st_id in courseReg["id_student"]:
        st_id = int(st_id)
        if st_id not in students_ids:
            students_ids.append(st_id)
    students = data.getStudentsInfo()
    students = students[students["id_student"].isin(students_ids)]
    students_unique = students.groupby('id_student').first()
    #get students info
    std_info,assessment_percentage,assesment_note,vle_day,acc = setStudentsInfo(students_unique,course, subject, time)
    return {"max_students":max_registered,"actual_students":len(students_unique),
        "percentage":assessment_percentage,"notes":assesment_note,"days":vle_day,"acc":acc,"std_info":std_info}
    
def setStudentsInfo(students,course,subject,time):
    std_info = []
    #get all assessments done until the date
    assessments = data.getAssessments()
    assessments = assessments[assessments["code_presentation"] == course]
    assessments = assessments[assessments["code_module"] == subject]
    assessments = assessments[assessments["date"] < int(time)]
    assessments_ids = assessments.id_assessment.unique()
    
    #get decision tree
    predictions = []
    if len(students)>1:
        predictions,assessment_list,assessment_percentage,assesment_note,vle_day,acc = setPrediction(students,course,subject,time)
    
    #for every student get what assessments has uploaded
    student_assessments = data.getStudentAssessments()
    prediction_count = 0
    for i,std in students.iterrows():
        std_assessments = []
        for assessment_id in assessments_ids:
            assessment = assessments[assessments["id_assessment"] == assessment_id]
            student_assessment = student_assessments[student_assessments["id_assessment"] == assessment_id]
            student_assessment = student_assessment[student_assessment["id_student"] == i]
            student_assessment = student_assessment[student_assessment["date_submitted"] < int(time)]
            assessment_type = str(assessment["assessment_type"].values[0])
            if(len(student_assessment)>=1):
                std_assessments.append({assessment_type:True})
            else:
                std_assessments.append({assessment_type:False})
        if len(predictions) > 1:
            std_info.append({"std_id": i, "region":std["region"],"highest_education":std["highest_education"],"imd_band":std["imd_band"],"age_band":std["age_band"],"disability":std["disability"], "assessments": std_assessments, "note":str(assessment_list[prediction_count]),"prediction": str(predictions[prediction_count])})
        else:
            std_info.append({"std_id": i, "region":std["region"], "highest_education":std["highest_education"],"imd_band":std["imd_band"],"age_band":std["age_band"],"disability":std["disability"],"assessments": std_assessments, "prediction": False})
        prediction_count += 1
    if len(predictions) > 1:
        return std_info,assessment_percentage,assesment_note,vle_day,acc
    else:
        return std_info

def setPrediction(students,course,subject,time):

    # buld my own dataset
    # get % entregas
    # get number of vl days
    # students unique
    students_data = students.copy()
    students_data,assessment_percentage = setAssesmentsPercentage(students_data,course,subject,time)
    students_data,assessment_list,assesment_note = setAssesmentsScore(students_data,course,subject,time)
    students_data,vle_day = setVleDays(students_data,course,subject)
    students_data = students_data[["highest_education","imd_band","num_of_prev_attempts","studied_credits",
                                    "disability","assesments_percentage","assesments_score","vle_days"]]
    # set withdrawn and fail as the same type
    students["final_result"] = students["final_result"].replace("Withdrawn",0)
    students["final_result"] = students["final_result"].replace("Fail",0)
    students["final_result"] = students["final_result"].replace("Pass",1)
    students["final_result"] = students["final_result"].replace("Distinction",1)
    # create decision tree
    # student_data = students.drop("final_result",axis=1)
    result_data = students["final_result"]
    student_data_encoded = pd.get_dummies(students_data,drop_first=True) #students_data for better predicction
    student_data_encoded = student_data_encoded.fillna(0)
    student_train,student_test,result_train,result_test = train_test_split(student_data_encoded,result_data,test_size=0.3)
    dtree = DecisionTreeClassifier(max_depth=4)
    dtree.fit(student_train,result_train)
    #get image of tree
    if time == 100:
        # fig = plt.figure(figsize=((25,20)))
        plot_tree(dtree,
                feature_names = student_data_encoded.columns,
                class_names=['no will pass', 'will pass'], 
                impurity=False,
                proportion=True,
                filled=True)
        fig.savefig('tree.png')
    #predicctions and accuracy
    predicitions = dtree.predict(student_data_encoded) #use student_test for test diferents accuracy
    acc = accuracy_score(result_data, predicitions)
    m_confusion = confusion_matrix(result_data, predicitions)
    print(acc)
    print(m_confusion)
    return predicitions,assessment_list,assessment_percentage,assesment_note,vle_day,round((acc*100),2)

    
def setAssesmentsPercentage(students,course,subject,time):
    #get all assessments done until the date
    assessments = data.getAssessments()
    assessments = assessments[assessments["code_presentation"] == course]
    assessments = assessments[assessments["code_module"] == subject]
    assessments = assessments[assessments["date"] < int(time)]
    assessments_ids = assessments.id_assessment.unique()
    #for every student get what assessments has uploaded
    student_assessments = data.getStudentAssessments()
    assessment_list = []
    for i,std in students.iterrows():
        assessments_count = 0
        std_count = 0
        for assessment_id in assessments_ids:
            assessments_count += 1
            student_assessment = student_assessments[student_assessments["id_assessment"] == assessment_id]
            student_assessment = student_assessment[student_assessment["id_student"] == i]
            student_assessment = student_assessment[student_assessment["date_submitted"] < int(time)]
            if(len(student_assessment)>=1):
                std_count += 1
        if assessments_count == 0:
            assessment_list.append(1)
        else:
            assessment_list.append(std_count/assessments_count)
    assessment_average = sum(assessment_list)/len(assessment_list)
    students["assesments_percentage"] = assessment_list
    return students,round((assessment_average*100),2)

def setAssesmentsScore(students,course,subject,time):
    #get all assessments done until the date
    assessments = data.getAssessments()
    assessments = assessments[assessments["code_presentation"] == course]
    assessments = assessments[assessments["code_module"] == subject]
    assessments = assessments[assessments["date"] < int(time)]
    assessments_ids = assessments.id_assessment.unique()
    #for every student get what assessments has uploaded
    student_assessments = data.getStudentAssessments()
    assessment_list = []
    for i,std in students.iterrows():
        assessments_count = 0
        score = 0
        for assessment_id in assessments_ids:
            assessments_count += 1
            student_assessment = student_assessments[student_assessments["id_assessment"] == assessment_id]
            student_assessment = student_assessment[student_assessment["id_student"] == i]
            student_assessment = student_assessment[student_assessment["date_submitted"] < int(time)]
            if student_assessment.shape[0] > 0:
                score += student_assessment["score"].item()
        if assessments_count == 0:
            assessment_list.append(0)
        else:
            assessment_list.append(score/assessments_count)
    assessment_note_average = sum(assessment_list)/len(assessment_list)
    students["assesments_score"] = assessment_list
    return students,assessment_list,round(assessment_note_average,2)

def setVleDays(students,course,subject):
    # get vle students data
    stdVle = data.getStudentVle()
    stdVle = stdVle[stdVle["code_presentation"] == course]
    stdVle = stdVle[stdVle["code_module"] == subject]
    # students iteration 
    vle_list = []
    for i,std in students.iterrows():
        studentVle = stdVle[stdVle["id_student"]==i]
        studentVle = studentVle.groupby('date').first()
        vle_list.append(len(studentVle))
    vle_average_day = sum(vle_list)/len(vle_list)
    students["vle_days"] = vle_list
    return students,round(vle_average_day,2)
        

@app.route('/', methods=['GET'])
def process():
    return ""

# carga todos los csv en la variable data i enciende el servidor
if __name__ == '__main__':
    assessments = pd.read_csv("DB/assessments.csv")
    courses = pd.read_csv("DB/courses.csv")
    vle = pd.read_csv("DB/vle.csv")
    studentAssessment = pd.read_csv("DB/studentAssessment.csv")
    studentInfo = pd.read_csv("DB/studentInfo.csv")
    studentRegistration = pd.read_csv("DB/studentRegistration.csv")
    studentVle = pd.read_csv("DB/studentVle.csv")
    users = pd.read_csv("DB/users.csv")
    teachers = pd.read_csv("DB/teachers.csv")
    data.setData(assessments,courses,studentAssessment, studentInfo, studentRegistration, studentVle ,vle, users, teachers)
    app.run(debug=True)