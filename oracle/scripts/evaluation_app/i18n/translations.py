"""
翻译字典 (Translation Dictionary)
包含所有UI文本的中英文版本
"""

TRANSLATIONS = {
    "zh": {
        "page": {
            "title": "医学AI评测系统",
            "icon": "🏥"
        },
        "sidebar": {
            "system_title": "医学AI评测系统",
            "user_info": "用户信息",
            "name": "姓名",
            "title": "职称",
            "specialty": "专科",
            "experience": "从业年限",
            "hospital": "医院级别",
            "logout": "退出登录",
            "instructions_title": "使用说明",
            "instructions": [
                "1. 首次使用请先注册账号",
                "2. 登录后选择评测任务",
                "3. 阅读患者病例信息",
                "4. 查看不同AI模型的回答",
                "5. 根据评分标准进行评价",
                "6. 提交评价后继续下一个病例"
            ]
        },
        "login": {
            "tab_login": "登录",
            "tab_register": "注册",
            "label_name": "姓名",
            "label_password": "密码",
            "label_title": "职称",
            "label_specialty": "专科",
            "label_experience": "从业年限",
            "label_hospital": "医院级别",
            "button_login": "登录",
            "button_register": "注册",
            "success_login": "登录成功！",
            "success_register": "注册成功！请登录。",
            "error_empty": "请填写所有字段",
            "error_wrong_password": "密码错误",
            "error_not_found": "用户不存在",
            "error_exists": "用户名已存在"
        },
        "task_selection": {
            "welcome": "欢迎，{name} {title}！",
            "select_task": "请选择评测任务",
            "task_name": "任务名称",
            "task_description": "任务描述",
            "progress": "进度",
            "completed": "已完成 {completed}/{total} 个病例",
            "button_start": "开始评测",
            "button_continue": "继续评测"
        },
        "evaluation": {
            "title": "病例评价",
            "progress": "进度：{current}/{total}",
            "patient_info": "患者信息",
            "model_answer": "模型回答",
            "evaluation_form": "评价表单",
            "dimension_accuracy": "准确性",
            "dimension_completeness": "完整性",
            "dimension_professionalism": "专业性",
            "dimension_practicality": "实用性",
            "dimension_overall": "总体评分",
            "label_score": "评分 (1-5分)",
            "label_comment": "评价意见（选填）",
            "placeholder_comment": "请输入您的评价意见...",
            "button_submit": "提交评价",
            "button_next": "下一个病例",
            "button_back": "返回任务列表",
            "success_submit": "评价提交成功！",
            "error_submit": "提交失败，请重试",
            "task_complete": "恭喜！您已完成本任务的所有病例评价。",
            "score_help": "1=很差，2=较差，3=一般，4=较好，5=很好",
            "ranking_error": "排序存在重复，请勾选'允许并列'或修改排序"
        },
        "config": {
            "title_options": ["住院医师", "主治医师", "副主任医师", "主任医师"],
            "experience_options": ["<5年", "5-10年", "10-20年", ">20年"],
            "hospital_options": ["三甲医院", "三乙医院", "二甲医院", "其他"],
            "specialty_options": ["骨科", "创伤骨科", "脊柱外科", "关节外科",
                                "康复科", "麻醉科", "内科", "其他"],
            "rating_dimensions": {
                "accuracy": "医学准确性",
                "completeness": "内容完整性",
                "safety": "临床安全性",
                "actionability": "可操作性",
                "clarity": "表述清晰度"
            }
        }
    },
    "en": {
        "page": {
            "title": "Medical AI Evaluation System",
            "icon": "🏥"
        },
        "sidebar": {
            "system_title": "Medical AI Evaluation System",
            "user_info": "User Information",
            "name": "Name",
            "title": "Title",
            "specialty": "Specialty",
            "experience": "Experience",
            "hospital": "Hospital Level",
            "logout": "Logout",
            "instructions_title": "Instructions",
            "instructions": [
                "1. Register an account for first-time use",
                "2. Select an evaluation task after login",
                "3. Read patient case information",
                "4. Review answers from different AI models",
                "5. Evaluate based on scoring criteria",
                "6. Submit evaluation and continue to next case"
            ]
        },
        "login": {
            "tab_login": "Login",
            "tab_register": "Register",
            "label_name": "Name",
            "label_password": "Password",
            "label_title": "Title",
            "label_specialty": "Specialty",
            "label_experience": "Experience",
            "label_hospital": "Hospital Level",
            "button_login": "Login",
            "button_register": "Register",
            "success_login": "Login successful!",
            "success_register": "Registration successful! Please login.",
            "error_empty": "Please fill in all fields",
            "error_wrong_password": "Incorrect password",
            "error_not_found": "User does not exist",
            "error_exists": "Username already exists"
        },
        "task_selection": {
            "welcome": "Welcome, {name} {title}!",
            "select_task": "Please select an evaluation task",
            "task_name": "Task Name",
            "task_description": "Task Description",
            "progress": "Progress",
            "completed": "Completed {completed}/{total} cases",
            "button_start": "Start Evaluation",
            "button_continue": "Continue Evaluation"
        },
        "evaluation": {
            "title": "Case Evaluation",
            "progress": "Progress: {current}/{total}",
            "patient_info": "Patient Information",
            "model_answer": "Model Answer",
            "evaluation_form": "Evaluation Form",
            "dimension_accuracy": "Accuracy",
            "dimension_completeness": "Completeness",
            "dimension_professionalism": "Professionalism",
            "dimension_practicality": "Practicality",
            "dimension_overall": "Overall Score",
            "label_score": "Score (1-5)",
            "label_comment": "Comments (Optional)",
            "placeholder_comment": "Please enter your comments...",
            "button_submit": "Submit Evaluation",
            "button_next": "Next Case",
            "button_back": "Back to Task List",
            "success_submit": "Evaluation submitted successfully!",
            "error_submit": "Submission failed, please try again",
            "task_complete": "Congratulations! You have completed all cases for this task.",
            "score_help": "1=Very Poor, 2=Poor, 3=Fair, 4=Good, 5=Excellent",
            "ranking_error": "Duplicate rankings found. Please check 'Allow ties' or modify rankings"
        },
        "config": {
            "title_options": ["Resident", "Attending Physician", "Associate Chief Physician", "Chief Physician"],
            "experience_options": ["<5 years", "5-10 years", "10-20 years", ">20 years"],
            "hospital_options": ["Tertiary A Hospital", "Tertiary B Hospital", "Secondary A Hospital", "Other"],
            "specialty_options": ["Orthopedics", "Trauma Orthopedics", "Spine Surgery", "Joint Surgery",
                                "Rehabilitation", "Anesthesiology", "Internal Medicine", "Other"],
            "rating_dimensions": {
                "accuracy": "Accuracy",
                "completeness": "Completeness",
                "safety": "Safety",
                "actionability": "Actionability",
                "clarity": "Clarity"
            }
        }
    }
}


def get_text(key_path, lang="zh", **kwargs):
    """
    根据键路径获取翻译文本

    Args:
        key_path: 点分隔的键路径，如 "sidebar.system_title"
        lang: 语言代码 ("zh" 或 "en")
        **kwargs: 格式化参数

    Returns:
        翻译后的文本
    """
    keys = key_path.split(".")
    value = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key, key_path)
        else:
            return key_path

    # 如果是字符串且有格式化参数，进行格式化
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value

    return value


def get_language_name(lang):
    """获取语言显示名称"""
    return "中文" if lang == "zh" else "English"

