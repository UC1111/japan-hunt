# Japan Hunt MVP

海外ユーザーの日本商品への購入需要を収集し、日本国内の商品情報と突き合わせてOpportunity Scoreを算出するMVP。

- Reddit検索RSSから需要候補を収集
- 商品候補を集約
- Pokémon Center Onlineの商品情報を取得
- SQLiteへ履歴保存
- 需要・購入意図・希少性・日本限定性・在庫からスコア化
- HTML変更時の異常検知で安全停止
- CSVレポート生成

まずはX自動投稿をせず、需要検証を優先します。

## 実行

```bash
pip install -r requirements.txt
python main.py
```

生成:
- data/japan_hunt.db
- data/opportunities.csv

## GitHub Actions

`.github/workflows/daily.yml` が6時間ごとに実行します。
取得件数が異常な場合は安全停止し、既存DBを壊しません。

HTML構造の変更を完全に防ぐことはできませんが、JSON-LD→複数selector→件数検証という多層構造にしています。


## v0.2: 海外価格差

需要が1件以上ある商品について、eBay公開検索ページから表示価格の中央値を取得し、
1 USD = 150 JPY の暫定換算でPrice Gapを計算します。

これは「実際の成約価格」ではなく「検索結果に表示される出品価格の中央値」です。
したがって、Price Gapだけで購入判断をせず、需要・在庫・購入意図と組み合わせます。

次の段階ではeBayの公式API等、より安定した価格データソースへ差し替える設計にします。

## 現在の収益導線

ZenMarketには公式アフィリエイト制度があり、新規登録や商品購入に応じた報酬体系を公開しています。
MVPではまだリンクを自動挿入していません。


## v0.3: 価格取得を壊れにくく

- 価格取得を `price_sources.py` に分離
- 24時間キャッシュ
- 検索結果が3件未満なら価格差を採用しない
- 極端な価格外れ値を抑制
- 価格取得失敗時は前回値を利用
- 異常な価格差（-99%未満 / +5000%超）は無効化
- `price_source`, `price_sample`, `price_gap_percent` をCSVへ保存

これにより、海外サイトのHTML変更や一時的な取得失敗でOpportunity Score全体が壊れにくくなります。

### 重要
eBayの公式Browse APIも存在しますが、APIキー等の運用が必要になるため、
ゼロ円・GitHub Actions前提のMVPでは公開検索を暫定利用しています。
将来APIへ交換できるよう価格取得モジュールを分離しています。


## v0.4: 需要急増検知

各商品候補について直近30回の需要件数を保存し、

- 前回比
- 成長率
- z-score
- Demand Spike Score

を計算します。

通常のOpportunity Scoreを85%、急増シグナルを15%として最終ランキングを作ります。
これにより「昔から人気」だけでなく「今急に探され始めた」を上位に持ってきます。

`post_candidates.py` は80点以上・在庫あり等の条件を満たす商品について、
英語投稿の候補文を最大3件生成します。

まだX/Redditへの自動投稿はしていません。
まず投稿候補を確認して誤検出を潰す段階です。

GitHub Actionsはscheduleで定期実行でき、workflow_dispatchによる手動実行も可能です。
GitHub公式ドキュメントではscheduleはUTCが既定で、混雑時に遅延する可能性があるため、
v0.4では毎時ちょうどを避けた時刻にしています。
