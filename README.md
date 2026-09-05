# 데일리 영단어 퀴즈 (Windows exe)

## 1. 실행 (개발 중 테스트)
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate

python main.py
```

## 2. 사용법
1. GPT 웹(chatgpt.com)에서 핸드아웃 사진을 올리고, 아래 형식으로 JSON을 뽑아달라고 요청
   ```
   { "day": 39, "words": [ {"word": "...", "pos": "...", "definition": "...", "example": "..."} ] }
   ```
The attached image is a daily vocabulary handout from an English language academy.
Extract the Day number and every word entry (word, part of speech, English definition, example sentence) from the image.
Respond ONLY in the following JSON format — no explanation, no code block markers (```), no other text, just pure JSON.

{
  "day": 39,
  "words": [
    {
      "word": "Flame",
      "pos": "n.",
      "definition": "the hot, glowing gas that can be seen when a fire is burning",
      "example": "They tried to put out the fire, but the flames grew higher.",
      "example_form": "flames"
    }
  ]
}

Notes:
- example_form must be the exact form of the word as it appears in the example sentence (plural, past tense, gerund, etc. — e.g. flame → flames, guess → guessed).
- Copy the definition and example exactly as written in the image — do not paraphrase or summarize.
- Include all words shown in the image; don't skip any.

2. **단어 등록** 탭에 그 JSON을 그대로 붙여넣고 "DB에 저장"
3. **퀴즈** 탭에서 정의를 보고 단어 입력 → Enter 또는 "확인"

데이터는 프로그램 폴더에 생성되는 `vocab.db` (SQLite) 파일 하나에 저장

## 3. exe로 패키징하기
```
pip install pyinstaller
pyinstaller --onefile --windowed --name VocabQuiz main.py
```
- 완성된 실행 파일: `dist/VocabQuiz.exe`

## 4. 주의할 점
- 붙여넣은 텍스트가 JSON 형식이 아니면 저장 시 오류 메시지가 떠요 (GPT가 앞뒤에 설명을 붙였다면 JSON 부분만 남기고 지워주세요)
- 퀴즈 채점은 현재 완전 일치(대소문자 무시)만 지원
