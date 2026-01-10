# NoaLog 作業分担計画

## 部署アサイン

### メイン担当: dev-manager（開発部）

**役割**: 全体の実装、アーキテクチャ設計、コードレビュー

**担当範囲**:
- Python環境・プロジェクト設定
- 全コアモジュールの実装
  - capture: 画面キャプチャ
  - hotkey: ホットキー管理
  - ocr: OCR処理
  - storage: データ永続化
- UI実装（PySide6）
- テストコード作成
- ビルド・配布設定

### サポート担当: tech-advisor-chief（技術監修部）

**役割**: 技術的正確性の検証、パフォーマンス監修

**担当範囲**:
- OCR精度検証
  - 前処理パラメータの最適化提案
  - 各種フォント・背景での認識テスト
- パフォーマンスレビュー
  - 応答性の計測・改善提案
  - メモリ使用量の監視
- クロスプラットフォーム互換性確認

---

## フェーズ別タスク割り当て

### Phase 1: MVP

| タスク | 担当 | 期間 | 依存 |
|--------|------|------|------|
| プロジェクト設定 | dev-manager | Day 1-2 | - |
| Capture実装 | dev-manager | Day 3-4 | プロジェクト設定 |
| Hotkey実装 | dev-manager | Day 5-7 | プロジェクト設定 |
| OCR実装 | dev-manager | Day 8-10 | Capture |
| OCR精度検証 | tech-advisor-chief | Day 10-11 | OCR実装 |
| Storage実装 | dev-manager | Day 11-12 | - |
| 構造化処理 | dev-manager | Day 13-14 | OCR, Storage |
| 基本UI | dev-manager | Day 15-17 | 全コアモジュール |
| ログビューア | dev-manager | Day 18-19 | Storage, UI |
| MVP統合テスト | dev-manager | Day 20-21 | 全機能 |

### Phase 2: Beta

| タスク | 担当 | 備考 |
|--------|------|------|
| 編集機能 | dev-manager | raw/edited分離 |
| コピー形式拡張 | dev-manager | Markdown等 |
| エクスポート | dev-manager | 複数形式対応 |
| 重複排除 | dev-manager | アルゴリズム設計 |
| UI/UX改善 | dev-manager | テーマ実装 |
| パフォーマンスレビュー | tech-advisor-chief | 中間チェック |

### Phase 3: 1.0

| タスク | 担当 | 備考 |
|--------|------|------|
| macOS署名 | dev-manager | Notarization |
| Windows対応 | dev-manager | インストーラー |
| パフォーマンス最適化 | dev-manager + tech-advisor-chief | 共同作業 |
| ドキュメント | dev-manager | ユーザー向け |
| 最終レビュー | tech-advisor-chief | 品質保証 |

---

## 連携フロー

### OCR精度検証フロー

```
dev-manager                    tech-advisor-chief
    |                               |
    | OCR実装完了                    |
    |------------------------------>|
    |                               | テスト画像で検証
    |                               | パラメータ調整提案
    |<------------------------------|
    | 前処理パラメータ調整           |
    |                               |
```

### パフォーマンスレビューフロー

```
dev-manager                    tech-advisor-chief
    |                               |
    | 機能実装完了                   |
    |------------------------------>|
    |                               | 応答性計測
    |                               | メモリプロファイリング
    |                               | 改善点レポート
    |<------------------------------|
    | 最適化実施                     |
    |                               |
```

---

## 成果物の受け渡し

### dev-manager -> tech-advisor-chief

**OCR検証依頼時**:
- 実行可能なOCRモジュール
- テスト用サンプル画像
- 現在の前処理設定
- 期待する認識結果

**パフォーマンスレビュー依頼時**:
- 実行可能なアプリケーション
- 使用シナリオ説明
- 現在のパフォーマンス計測結果

### tech-advisor-chief -> dev-manager

**OCR検証結果**:
- 各サンプルでの認識結果
- 認識率レポート
- 前処理パラメータ調整提案
- 問題パターンの特定

**パフォーマンスレビュー結果**:
- 応答性計測データ
- メモリ使用量グラフ
- ボトルネック分析
- 最適化提案

---

## コミュニケーション

### レポート

- 各担当者は作業完了時に `/Users/dansetsu/NoaLog/reports/` にレポートを作成
- chief-producerが進捗を統合管理

### 問題発生時

1. 問題を発見した担当者がissueとして記録
2. chief-producerに報告
3. 必要に応じて担当者間で協議
4. 解決策を決定・実施

---

## タブ配置計画

```
タブ0: chief-producer   - プロジェクト統括
タブ1: dev-manager      - メイン開発
タブ2: tech-advisor-chief - 技術監修（必要時）
```

---

最終更新: 2026-01-04
