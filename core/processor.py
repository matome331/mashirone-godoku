import re
import html

class MisreadingProcessor:
    def __init__(self):
        # 抽出ルール: タイムスタンプ(必須) ひらがな(必須) (元の言葉/漢字・英語)
        # 例: "1:46:41 あんなんばん（案内板）"
        self.pattern = re.compile(
            r'(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?)'           # タイムスタンプ（必須）
            r'\s+'                                               # スペース
            r'(?P<reading>[ぁ-んー]+)'                             # 読み（ひらがな限定・必須）
            r'\s*[\(（]'                                         # 括弧の開始
            r'(?P<original>[^）\)\s]+)'                           # 元の言葉（漢字や英語）
            r'[\)）]'                                            # 括弧の終了
            r'(?:\s*[(（](?P<context>[^)）]+)[)）])?'             # 補足コンテキスト（任意）
        )
        
        # 除外キーワードリストの読み込み
        self.exclude_keywords = []
        # 絶対パスで取得
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exclude_path = os.path.join(base_dir, "exclude_keywords.txt")
        if os.path.exists(exclude_path):
            with open(exclude_path, "r", encoding="utf-8") as f:
                self.exclude_keywords = [line.strip() for line in f if line.strip()]

    def parse_comments(self, comments):
        """Parse raw comments and extract misreading entries."""
        extracted_items = []
        for comment in comments:
            text = comment.get('text', '')
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue

                # 1. 除外リストに従って行をスキップ
                if any(kw in line for kw in self.exclude_keywords):
                    continue

                # 2. 厳格なルールに合致するかチェック
                match = self.pattern.search(line)
                if match:
                    extracted_items.append({
                        'timestamp': match.group('timestamp') or "0:00",
                        'original': self._sanitize(match.group('original')),
                        'reading': self._sanitize(match.group('reading')),
                        'context': self._sanitize(match.group('context')) if match.group('context') else ""
                    })
        return extracted_items

    def _sanitize(self, text):
        """Sanitize text to prevent XSS and other injection issues."""
        if not text: return ""
        # 1. Escape HTML special characters
        text = html.escape(text)
        # 2. Remove any potential control characters or weird whitespace
        text = "".join(char for char in text if char.isprintable())
        return text.strip()

if __name__ == "__main__":
    # Test
    processor = MisreadingProcessor()
    test_comments = [
        {'text': '12:34 走馬灯 -> そうまとう'},
        {'text': '[01:05:22] 杞憂 -> きゆう (心配しすぎ)'},
        {'text': '5:00 <script>alert(1)</script> -> 安全な読込'}, # Security test
        {'text': 'これは関係ないコメント'}
    ]
    results = processor.parse_comments(test_comments)
    for res in results:
        print(f"Parsed: {res['timestamp']} | {res['original']} -> {res['reading']} | Context: {res['context']}")
