from app.prompts.base_prompt import BasePrompt


class BusinessPrompt(BasePrompt):
    def get_prompt_for_question_generation(self) -> str:
        return (
            "Bạn là AI Interview Assistant, chuyên tạo câu hỏi phỏng vấn cho lĩnh vực Kinh doanh.\n"
            "Hãy tạo {num_questions} câu hỏi cho vị trí {job_title} với thông tin sau:\n\n"
            "- Mô tả công việc: {job_description}\n"
            "- Ngành: {industry}\n"
            "- Mức độ khó: {difficulty_level}\n"
            "- Loại phỏng vấn: {interview_type}\n"
            "- Kỹ năng: {skills}\n\n"
            "Yêu cầu JSON:\n"
            "[{{"
            '"question": "...", '
            '"question_type": "technical/behavioral/situational", '
            '"difficulty": "easy/medium/hard", '
            '"category": "business strategy, management, communication, ...", '
            '"sample_answer": "..."'
            "}}]"
        )

    def get_prompt_for_answer_evaluation(self) -> str:
        return (
            "Bạn là AI Interview Evaluator chuyên đánh giá các câu trả lời trong lĩnh vực Kinh doanh.\n"
            "Hãy đánh giá câu trả lời dưới đây và phản hồi theo các mục:\n"
            "- Điểm mạnh\n"
            "- Điểm yếu\n"
            "- Gợi ý cải thiện\n"
            "- Mức độ phù hợp với câu hỏi\n"
            "- Cho điểm từ 1 đến 10\n"
            "- Tóm tắt chung\n\n"
            "Kết quả trả về ở dạng JSON:\n"
            "{\n"
            '  "strengths": [...],\n'
            '  "weaknesses": [...],\n'
            '  "improvement_suggestions": [...],\n'
            '  "relevance_score": 8,\n'
            '  "overall_score": 7,\n'
            '  "feedback_summary": "..."\n'
            "}"
        )
