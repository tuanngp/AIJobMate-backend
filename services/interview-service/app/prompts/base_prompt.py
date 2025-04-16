from abc import ABC, abstractmethod

class BasePrompt(ABC):
    @abstractmethod
    def get_prompt_for_question_generation(self) -> str:
        pass

    @abstractmethod
    def get_prompt_for_answer_evaluation(self) -> str:
        pass
