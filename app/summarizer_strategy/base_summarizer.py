from abc import ABC, abstractmethod
from typing import Generator, Tuple, Optional, List

class SummarizerStrategy(ABC):
    @abstractmethod
    def summarize_with_logs(
            self,
            file_path: str,
    ) -> Generator[Tuple[str, str], None, None]:
        pass
