import os
import re
import time
import json
import subprocess
import requests
from bs4 import BeautifulSoup

# ==================== システム設定項目 ====================
WRITENING_URL = "https://writening.net/page?XwwNSm"
INTERVAL_SECONDS = 30  # 巡回チェックの間隔（秒）

# あなたの正しいフォルダパス
HTML_FILE_PATH = "nazonazo/index.html"
# =========================================================

def fetch_and_parse_riddles():
    """Writeningから最新のクイズデータをダウンロードして解析する"""
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Writening.netをパトロール中...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(WRITENING_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content_element = soup.find(class_="section-item")
        
        if not content_element:
            print("[警告] Writeningの本文(section-item)が見つかりませんでした。")
            return None
            
        raw_text = content_element.get_text(strip=True)
        matches = re.findall(r'\{(.*?)\}', raw_text)
        
        parsed_list = []
        for match in matches:
            parts = match.split('|')
            if len(parts) >= 2:
                parsed_list.append({
                    "question": parts[0],
                    "answer": parts[1],
                    "explanation": parts[2] if len(parts) > 2 else ""
                })
        return parsed_list
    except Exception as e:
        print(f"[通信エラー] データの取得に失敗しました: {e}")
        return None

def update_html_file(riddles_data):
    """新しいHTMLの仕様に合わせて、末尾にupdateRiddles命令を安全に埋め込む"""
    if not os.path.exists(HTML_FILE_PATH):
        print(f"[致命的エラー] 指定されたパスにHTMLファイルが存在しません: {HTML_FILE_PATH}")
        return False
            
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # なぞなぞデータを綺麗なJSON形式に変換
    riddles_json = json.dumps(riddles_data, ensure_ascii=False)
    
    # 新しいHTMLを起動するための専用命令文を作成
    # ページが読み込まれた後に自動でupdateRiddlesを実行させる仕掛けです
    injection_code = f"\n<script>window.addEventListener('DOMContentLoaded', () => {{ setTimeout(() => {{ updateRiddles({riddles_json}); }}, 300); }});</script>\n"
    
    # 過去に埋め込んだ古い自動起動スクリプトが残っていれば、蓄積を防ぐために一旦消去するクレンジング処理
    content = re.sub(r'<script>window\.addEventListener\(\'DOMContentLoaded\'.*?<\/script>', '', content, flags=re.DOTALL)
    
    # </body>タグの直前に、新しい自動起動命令をスッと挟み込む
    if "</body>" in content:
        new_content = content.replace("</body>", f"{injection_code}</body>")
    else:
        # 万が一</body>がなくても末尾に追加
        new_content = content + injection_code
    
    # 前回の内容と完全に一致＝変化がない場合は送信をスキップ
    if content == new_content:
        return False
        
    with open(HTML_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[データ注入成功] 『{HTML_FILE_PATH}』の内部スイッチをONにし、{len(riddles_data)}問をセットしました。")
    return True

def push_to_github():
    """最新の「main」ブランチへ正確にコミット＆プッシュ（送信）する"""
    print("[GitHub送信] 変更をキャッチ。GitHubへ最新データを転送中...")
    try:
        # 変更されたファイルをGitの追跡対象に加える
        subprocess.run(["git", "add", "."], check=True)
        
        # コミットメッセージの作成
        commit_msg = f"Riddle Flow API Sync: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # 確実に「main」ブランチに対して送信を行います
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🎉 【完全大成功】GitHubへのデータ転送が完了しました！")
    except subprocess.CalledProcessError as e:
        print(f"[Gitエラー] 転送中にエラーが発生しました: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("🚀 【Riddle Flow専用・API完全適合版】同期システム起動")
    print(f"   ターゲットファイル: {HTML_FILE_PATH}")
    print(f"   パトロール間隔    : {INTERVAL_SECONDS}秒ごと")
    print("==================================================")
    
    try:
        while True:
            riddles = fetch_and_parse_riddles()
            if riddles:
                is_changed = update_html_file(riddles)
                if is_changed:
                    push_to_github()
                else:
                    print("[変更なし] Writeningに変化はありません。送信をパスしました。")
                    
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[停止] システムを安全に終了しました。")
