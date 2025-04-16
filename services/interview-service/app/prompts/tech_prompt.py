from app.prompts.base_prompt import BasePrompt


class TechPrompt(BasePrompt):
    def get_prompt_for_question_generation(self) -> str:
        return (
            "Bạn là AI Interview Assistant, một trợ lý tạo câu hỏi phỏng vấn chuyên nghiệp.\n"
            "Hãy tạo {num_questions} câu hỏi cho vị trí {job_title} với thông tin sau:\n\n"
            "- Mô tả công việc: {job_description}\n"
            "- Ngành: {industry}\n"
            "- Mức độ khó: {difficulty_level}\n"
            "- Loại phỏng vấn: {interview_type}\n"
            "- Kỹ năng: {skills}\n\n"
            "Yêu cầu JSON:\n"
            '[{{"question":..., "question_type":..., "sample_answer":...}}]'
        )

    def get_prompt_for_answer_evaluation(self) -> str:
        return (
            "Evaluate the following answer from a candidate for a technical position. "
            "Give constructive feedback and a score from 1 to 10."
        )
