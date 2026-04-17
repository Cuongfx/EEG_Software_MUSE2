from __future__ import annotations

import csv
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox

from .config import NBackRules, calculate_trial_count, load_rules
from .data import load_participant_tasks, resolve_block_plan
from .master_control import append_master_control_row, ensure_master_control_workbook
from .models import ExaminerSession, SessionStage, TrialResult


LANGUAGE_LABELS = {
    "en": "English",
    "de": "Deutsch",
    "vi": "Tiếng Việt",
}

CONSENT_TEXT = {
    "en": """EEG Study Participation – Detailed Terms, Conditions, and Informed Consent

1. Study Overview
You are invited to participate in a research study involving the recording of electroencephalography (EEG) signals. EEG measures electrical activity in the brain using non-invasive sensors placed on the scalp.

This study is conducted solely for academic, scientific, and non-commercial purposes, including the creation of an open-access dataset for research use.

2. Voluntary Participation
Your participation is entirely voluntary.

By agreeing to participate, you confirm that:
- You are participating of your own free will
- You are at least 18 years old (or have legal guardian consent if required)
- You may withdraw at any time without penalty, explanation, or consequence
- Withdrawal will not affect you in any way

3. Purpose of Data Collection
The purpose of this study is to:
- Record EEG signals under controlled experimental conditions
- Analyze brain activity for scientific research
- Create a dataset that may be shared publicly with the research community

4. Procedures
If you agree to participate:
- EEG sensors will be placed on your scalp
- You may be asked to perform simple tasks (e.g., resting, responding to stimuli, or cognitive tasks)
- The session duration will typically range from [X] to [X] minutes

No invasive procedures will be conducted.

5. Data Collected
The study will collect the following data:
- EEG recordings (brain signal data)
- Age (numerical or age range)

The study will NOT collect or publish:
- Name
- Address
- Email or contact information
- Identification numbers
- Facial images, voice recordings, or video (unless explicitly stated separately)

6. Data Anonymization and Protection
To protect your identity:
- Your data will be assigned a random subject ID
- All personally identifiable information (PII) will be removed before any data sharing
- Data will be stored securely and handled in accordance with applicable data protection regulations (e.g., GDPR)

7. Public Data Sharing and Open Access
By participating, you explicitly consent that:
- Your EEG data and age may be made publicly available
- The dataset may be shared on open platforms (e.g., research repositories such as OpenNeuro, PhysioNet, Zenodo, etc.)
- Researchers worldwide may access, download, and use the dataset for scientific purposes

You acknowledge and understand that:
- Once data is made public, it may not be possible to fully withdraw it from all users or platforms
- Your data will remain anonymized and will not include direct personal identifiers

8. Legal Basis and Data Protection (GDPR Compliance)
This study processes your data based on your explicit consent.

Under applicable data protection laws, you have the right to:
- Access your data
- Request correction of inaccuracies
- Request deletion of your data (before public release)
- Withdraw consent at any time prior to data publication

After anonymized data is publicly released, full deletion may no longer be feasible.

9. Risks and Discomfort
EEG recording is a non-invasive and low-risk procedure.

Possible minor discomforts include:
- Mild pressure or discomfort from EEG sensors
- Temporary inconvenience during the recording session

No known significant physical or psychological risks are expected.

10. Benefits
You may not receive direct personal benefits from participation.
However, your contribution will support:
- Scientific research
- Development of open datasets
- Advancements in neuroscience and related fields

11. Compensation
This study is conducted on a voluntary, non-profit basis.
No financial compensation is provided for participation.

12. Withdrawal and Data Handling
You may withdraw:
- At any time during the experiment
- Before your data is anonymized and published

Upon withdrawal:
- Your identifiable data (if any) will be deleted
- Anonymized data already included in a public dataset may not be removable

13. Consent Statement
By signing below (or agreeing electronically), you confirm that:

- You have read and understood this document in full
- You voluntarily agree to participate in this study
- You understand the nature, purpose, and procedures of the experiment
- You consent to the collection and public sharing of your EEG data and age only
- You understand that no other personal identifying information will be made public
- You understand the limits of withdrawing data after public release
""",
    "de": """EEG-Studienteilnahme – Ausführliche Bedingungen und informierte Einwilligung

1. Überblick über die Studie
Sie sind eingeladen, an einer Forschungsstudie teilzunehmen, bei der Elektroenzephalographie-(EEG)-Signale aufgezeichnet werden. EEG misst die elektrische Aktivität des Gehirns mit nicht-invasiven Sensoren auf der Kopfhaut.

Diese Studie wird ausschließlich zu akademischen, wissenschaftlichen und nicht-kommerziellen Zwecken durchgeführt, einschließlich der Erstellung eines offen zugänglichen Datensatzes für die Forschung.

2. Freiwillige Teilnahme
Ihre Teilnahme ist vollständig freiwillig.

Mit Ihrer Zustimmung bestätigen Sie:
- Sie nehmen aus freiem Willen teil
- Sie sind mindestens 18 Jahre alt (oder verfügen, falls erforderlich, über die Zustimmung eines gesetzlichen Vertreters)
- Sie können jederzeit ohne Strafe, Begründung oder Nachteile zurücktreten
- Ein Rücktritt hat keine negativen Folgen für Sie

3. Zweck der Datenerhebung
Der Zweck dieser Studie ist:
- EEG-Signale unter kontrollierten Versuchsbedingungen aufzuzeichnen
- Gehirnaktivität für wissenschaftliche Forschung zu analysieren
- Einen Datensatz zu erstellen, der öffentlich mit der Forschungsgemeinschaft geteilt werden kann

4. Ablauf
Wenn Sie zustimmen:
- EEG-Sensoren werden auf Ihrer Kopfhaut angebracht
- Sie werden möglicherweise gebeten, einfache Aufgaben auszuführen (z. B. ruhen, auf Reize reagieren oder kognitive Aufgaben)
- Die Sitzungsdauer beträgt typischerweise zwischen [X] und [X] Minuten

Es werden keine invasiven Verfahren durchgeführt.

5. Erhobene Daten
Die Studie erhebt folgende Daten:
- EEG-Aufzeichnungen (Gehirnsignaldaten)
- Alter (numerisch oder Altersbereich)

Die Studie erhebt oder veröffentlicht NICHT:
- Name
- Adresse
- E-Mail- oder Kontaktdaten
- Identifikationsnummern
- Gesichtsbilder, Sprachaufnahmen oder Video (außer wenn dies separat ausdrücklich angegeben wird)

6. Anonymisierung und Schutz der Daten
Zum Schutz Ihrer Identität:
- Ihren Daten wird eine zufällige Probanden-ID zugewiesen
- Alle personenbezogenen Daten werden vor einer Weitergabe entfernt
- Die Daten werden sicher gespeichert und gemäß geltenden Datenschutzvorschriften (z. B. DSGVO) verarbeitet

7. Öffentliche Datenfreigabe und Open Access
Mit Ihrer Teilnahme stimmen Sie ausdrücklich zu, dass:
- Ihre EEG-Daten und Ihr Alter öffentlich verfügbar gemacht werden können
- Der Datensatz auf offenen Plattformen geteilt werden kann (z. B. Forschungsrepositorien wie OpenNeuro, PhysioNet, Zenodo usw.)
- Forschende weltweit auf den Datensatz zugreifen, ihn herunterladen und für wissenschaftliche Zwecke nutzen können

Sie erkennen an und verstehen, dass:
- Es nach einer öffentlichen Freigabe möglicherweise nicht mehr möglich ist, die Daten vollständig von allen Nutzern oder Plattformen zurückzuziehen
- Ihre Daten anonymisiert bleiben und keine direkten personenbezogenen Identifikatoren enthalten

8. Rechtsgrundlage und Datenschutz (DSGVO)
Diese Studie verarbeitet Ihre Daten auf Grundlage Ihrer ausdrücklichen Einwilligung.

Nach geltendem Datenschutzrecht haben Sie das Recht:
- Auf Ihre Daten zuzugreifen
- Die Berichtigung unrichtiger Daten zu verlangen
- Die Löschung Ihrer Daten zu verlangen (vor der öffentlichen Freigabe)
- Ihre Einwilligung jederzeit vor der Veröffentlichung der Daten zu widerrufen

Nachdem anonymisierte Daten öffentlich freigegeben wurden, ist eine vollständige Löschung möglicherweise nicht mehr möglich.

9. Risiken und Unannehmlichkeiten
Die EEG-Aufzeichnung ist nicht-invasiv und mit geringem Risiko verbunden.

Mögliche geringe Unannehmlichkeiten sind:
- Leichter Druck oder Unbehagen durch die EEG-Sensoren
- Vorübergehende Unannehmlichkeiten während der Aufzeichnung

Es sind keine bekannten erheblichen physischen oder psychischen Risiken zu erwarten.

10. Nutzen
Möglicherweise erhalten Sie keinen direkten persönlichen Nutzen aus der Teilnahme.
Ihr Beitrag unterstützt jedoch:
- Wissenschaftliche Forschung
- Die Entwicklung offener Datensätze
- Fortschritte in den Neurowissenschaften und verwandten Bereichen

11. Vergütung
Diese Studie wird auf freiwilliger, nicht-kommerzieller Basis durchgeführt.
Es wird keine finanzielle Vergütung für die Teilnahme gewährt.

12. Rücktritt und Datenverarbeitung
Sie können zurücktreten:
- Jederzeit während des Experiments
- Bevor Ihre Daten anonymisiert und veröffentlicht werden

Im Falle eines Rücktritts:
- Ihre identifizierbaren Daten (falls vorhanden) werden gelöscht
- Bereits in einem öffentlichen Datensatz enthaltene anonymisierte Daten können möglicherweise nicht entfernt werden

13. Einwilligungserklärung
Mit Ihrer Unterschrift unten (oder elektronischen Zustimmung) bestätigen Sie:

- Sie haben dieses Dokument vollständig gelesen und verstanden
- Sie stimmen der Teilnahme an dieser Studie freiwillig zu
- Sie verstehen Art, Zweck und Ablauf des Experiments
- Sie stimmen der Erhebung und öffentlichen Freigabe ausschließlich Ihrer EEG-Daten und Ihres Alters zu
- Sie verstehen, dass keine weiteren personenbezogenen Daten öffentlich gemacht werden
- Sie verstehen die Grenzen des Datenrücktritts nach öffentlicher Freigabe
""",
    "vi": """Tham gia nghiên cứu EEG – Điều khoản, điều kiện và chấp thuận tham gia chi tiết

1. Tổng quan nghiên cứu
Bạn được mời tham gia một nghiên cứu có ghi lại tín hiệu điện não đồ (EEG). EEG đo hoạt động điện của não bằng các cảm biến không xâm lấn đặt trên da đầu.

Nghiên cứu này chỉ được thực hiện cho mục đích học thuật, khoa học và phi thương mại, bao gồm việc tạo ra một bộ dữ liệu truy cập mở phục vụ nghiên cứu.

2. Tự nguyện tham gia
Việc tham gia hoàn toàn là tự nguyện.

Bằng việc đồng ý tham gia, bạn xác nhận rằng:
- Bạn tham gia hoàn toàn tự nguyện
- Bạn từ 18 tuổi trở lên (hoặc có sự đồng ý của người giám hộ hợp pháp nếu được yêu cầu)
- Bạn có thể rút lui bất kỳ lúc nào mà không bị phạt, không cần giải thích và không chịu hậu quả nào
- Việc rút lui sẽ không ảnh hưởng đến bạn theo bất kỳ cách nào

3. Mục đích thu thập dữ liệu
Mục đích của nghiên cứu này là:
- Ghi lại tín hiệu EEG trong điều kiện thí nghiệm có kiểm soát
- Phân tích hoạt động não phục vụ nghiên cứu khoa học
- Tạo ra một bộ dữ liệu có thể được chia sẻ công khai với cộng đồng nghiên cứu

4. Quy trình
Nếu bạn đồng ý tham gia:
- Các cảm biến EEG sẽ được đặt lên da đầu của bạn
- Bạn có thể được yêu cầu thực hiện các nhiệm vụ đơn giản (ví dụ: nghỉ ngơi, phản hồi kích thích hoặc làm nhiệm vụ nhận thức)
- Thời lượng phiên thường kéo dài từ [X] đến [X] phút

Sẽ không có thủ thuật xâm lấn nào được thực hiện.

5. Dữ liệu được thu thập
Nghiên cứu sẽ thu thập các dữ liệu sau:
- Bản ghi EEG (dữ liệu tín hiệu não)
- Tuổi (số tuổi hoặc nhóm tuổi)

Nghiên cứu sẽ KHÔNG thu thập hoặc công bố:
- Tên
- Địa chỉ
- Email hoặc thông tin liên hệ
- Số định danh
- Hình ảnh khuôn mặt, bản ghi giọng nói hoặc video (trừ khi có nêu rõ riêng)

6. Ẩn danh và bảo vệ dữ liệu
Để bảo vệ danh tính của bạn:
- Dữ liệu của bạn sẽ được gán một mã đối tượng ngẫu nhiên
- Mọi thông tin nhận dạng cá nhân sẽ được loại bỏ trước khi dữ liệu được chia sẻ
- Dữ liệu sẽ được lưu trữ an toàn và xử lý theo các quy định bảo vệ dữ liệu hiện hành (ví dụ: GDPR)

7. Chia sẻ dữ liệu công khai và truy cập mở
Bằng việc tham gia, bạn đồng ý rõ ràng rằng:
- Dữ liệu EEG và tuổi của bạn có thể được công khai
- Bộ dữ liệu có thể được chia sẻ trên các nền tảng mở (ví dụ: OpenNeuro, PhysioNet, Zenodo hoặc các kho nghiên cứu khác)
- Các nhà nghiên cứu trên toàn thế giới có thể truy cập, tải xuống và sử dụng bộ dữ liệu cho mục đích khoa học

Bạn xác nhận và hiểu rằng:
- Khi dữ liệu đã được công khai, có thể không thể rút dữ liệu hoàn toàn khỏi mọi người dùng hoặc nền tảng
- Dữ liệu của bạn sẽ được ẩn danh và không chứa định danh cá nhân trực tiếp

8. Cơ sở pháp lý và bảo vệ dữ liệu (tuân thủ GDPR)
Nghiên cứu này xử lý dữ liệu của bạn dựa trên sự đồng ý rõ ràng của bạn.

Theo các luật bảo vệ dữ liệu hiện hành, bạn có quyền:
- Truy cập dữ liệu của mình
- Yêu cầu chỉnh sửa thông tin không chính xác
- Yêu cầu xóa dữ liệu của mình (trước khi công bố công khai)
- Rút lại sự đồng ý bất kỳ lúc nào trước khi dữ liệu được công bố

Sau khi dữ liệu ẩn danh đã được công bố công khai, việc xóa hoàn toàn có thể không còn khả thi.

9. Rủi ro và khó chịu
Việc ghi EEG là không xâm lấn và có rủi ro thấp.

Một số khó chịu nhỏ có thể gồm:
- Áp lực nhẹ hoặc khó chịu do cảm biến EEG
- Sự bất tiện tạm thời trong thời gian ghi

Không có rủi ro thể chất hoặc tâm lý nghiêm trọng nào đã biết được dự kiến xảy ra.

10. Lợi ích
Bạn có thể không nhận được lợi ích cá nhân trực tiếp khi tham gia.
Tuy nhiên, sự đóng góp của bạn sẽ hỗ trợ:
- Nghiên cứu khoa học
- Phát triển các bộ dữ liệu mở
- Tiến bộ trong khoa học thần kinh và các lĩnh vực liên quan

11. Bồi dưỡng
Nghiên cứu này được thực hiện trên cơ sở tự nguyện, phi lợi nhuận.
Không có khoản bồi dưỡng tài chính nào cho việc tham gia.

12. Rút lui và xử lý dữ liệu
Bạn có thể rút lui:
- Bất kỳ lúc nào trong quá trình thí nghiệm
- Trước khi dữ liệu của bạn được ẩn danh và công bố

Khi rút lui:
- Dữ liệu có thể nhận dạng của bạn (nếu có) sẽ bị xóa
- Dữ liệu ẩn danh đã được đưa vào bộ dữ liệu công khai có thể không thể xóa bỏ

13. Tuyên bố đồng ý
Bằng việc ký bên dưới (hoặc đồng ý điện tử), bạn xác nhận rằng:

- Bạn đã đọc và hiểu đầy đủ tài liệu này
- Bạn tự nguyện đồng ý tham gia nghiên cứu này
- Bạn hiểu bản chất, mục đích và quy trình của thí nghiệm
- Bạn đồng ý cho việc thu thập và chia sẻ công khai chỉ dữ liệu EEG và tuổi của mình
- Bạn hiểu rằng sẽ không có thông tin định danh cá nhân nào khác được công khai
- Bạn hiểu giới hạn của việc rút dữ liệu sau khi công khai
""",
}

TRANSLATIONS = {
    "en": {
        "game_title": "Focus Game",
        "examiner_title": "Examiner Control",
        "waiting_for_examiner": "Waiting for Examiner...",
        "participant_locked": "The participant screen will unlock after the examiner confirms the session.",
        "start_button": "Start",
        "examiner_heading": "Examiner Control",
        "examiner_subtitle": "Fill in participant details and define the Relax, Break, and Game session order before the participant starts.",
        "name": "Name",
        "participant_id": "ID",
        "age": "Age",
        "n_value": "N Value",
        "relax_audio": "Play alpha audio during Relax",
        "note": "Note",
        "language": "Language",
        "session_planner": "Session Planner",
        "session": "Session",
        "order": "Order",
        "duration_minutes": "Duration (minutes)",
        "relax": "Relax",
        "break": "Break",
        "game": "Game",
        "planner_help": "Use order 1, 2, and 3 exactly once. Set any stage duration to 0 if you want to skip that stage, but Game must be greater than 0.",
        "awaiting_details": "Awaiting session details.",
        "confirm_session": "Confirm Session",
        "session_running_message": "The game is already running. Open a new game window if you want another session.",
        "name_required": "Name is required.",
        "id_required": "ID is required.",
        "age_required": "Age is required.",
        "n_value_required": "N value is required.",
        "n_value_integer": "N value must be a whole number.",
        "n_value_positive": "N value must be at least 1.",
        "session_confirmed_status": "Session confirmed for {participant_name}.\nOrder: {summary}\nBlock plan: {block_plan} ({data_source}).",
        "examiner_confirmed": "Examiner confirmed the session.",
        "participant_ready": "Participant: {participant_name}\nSession order: {summary}\nLanguage: {language}\n\nPress Start to begin the full block.",
        "order_whole_number": "{stage} order must be a whole number.",
        "duration_number": "{stage} duration must be a number.",
        "order_range": "{stage} order must be 1, 2, or 3.",
        "duration_negative": "{stage} duration can not be negative.",
        "order_unique": "Relax, Break, and Game must use order 1, 2, and 3 exactly once.",
        "game_duration_positive": "Game duration must be greater than zero.",
        "please_relax": "Please relax untill you hear the sound",
        "please_break": "Please Break untill you hear the sound",
        "time_remaining": "Time remaining: {minutes:02}:{seconds:02}",
        "preparing_next": "Preparing the next session...",
        "game_intro_title": "Game Session",
        "game_intro_detail": "You are about to begin the Focus Game.\n\nPress SPACE to continue through the instructions.",
        "how_to_play": "How To Play",
        "how_to_play_detail": "This is a {n_value}-back task.\n\nA sequence of letters will appear one at a time.\nPress SPACE only when the current letter matches the one shown {n_value} step(s) before.",
        "ready_to_start": "Ready To Start",
        "ready_to_start_detail": "Stay focused for {duration:g} minute(s).\n\nPress SPACE when you are ready to start the game.",
        "block_ended": "Congratulation, the Block is ended",
        "experiment_finished_saved": "The Experiment is finished. Thank you for your attention!\n\nFinal score: {score:.2f}\n\nSaved: {filename}",
        "experiment_finished": "The Experiment is finished. Thank you for your attention!\n\nFinal score: {score:.2f}",
        "launch_failed_title": "Focus Game",
        "launch_failed_message": "Failed to start the game: {error}",
        "consent_title": "Consent Required",
        "consent_intro": "Please read the study terms below and confirm your consent before starting the game.",
        "consent_agree": "I agree to participate in this EEG study.",
        "consent_open_button": "Terms and Conditions",
        "consent_prompt": "Please read the Terms and Conditions before starting the game.",
        "demo_title": "Demo Mode",
        "demo_intro_detail": "This guided demo uses {n_value}-back.\n\nYou will play 4 short practice rounds that explain the rule step by step before the real game.\n\n{sliding_rule}",
        "demo_start": "Start Demo",
        "demo_round_title": "Demo Round {current}/{total}",
        "demo_play_round": "Play Round",
        "demo_next_round": "Next Round",
        "demo_round_complete": "Round Complete",
        "demo_complete_title": "Demo is complete",
        "demo_complete_detail": "You have finished the guided demo.\n\nYou can start the demo again or close this window.",
        "demo_restart": "Start Demo Again",
        "demo_close": "Close",
        "demo_feedback_perfect": "Well done. You responded correctly in this round.",
        "demo_feedback_missed": "Almost there. You missed at least one required SPACE press in this round.",
        "demo_feedback_extra": "Almost there. You pressed SPACE when there was no match in this round.",
        "demo_feedback_mixed": "This round had both missed matches and extra SPACE presses. Try the next one slowly.",
        "demo_round_1_intro": "Round 1 builds the rule. For the first {n_value} letters, just remember them. Press SPACE on the final letter because it matches the first letter from {n_value} steps earlier.",
        "demo_round_1_prompt": "Watch the letters. Press SPACE only on the final letter.",
        "demo_round_1_summary": "The last letter matched the first letter from {n_value} steps earlier. That is when you should press SPACE.",
        "demo_round_2_intro": "Round 2 shows a non-match. Do not press SPACE on the final letter if it is different from the letter {n_value} steps earlier.",
        "demo_round_2_prompt": "Do not press SPACE unless the new letter matches {n_value} steps back.",
        "demo_round_2_summary": "The last letter did not match the letter {n_value} steps earlier, so the correct action was no key press.",
        "demo_round_3_intro": "Round 3 mixes one match and one non-match. Press SPACE only when the matching letter appears.",
        "demo_round_3_prompt": "One new letter is a match. Press SPACE only for that one.",
        "demo_round_3_summary": "A match needs SPACE, and a non-match needs no response.",
        "demo_round_4_intro": "Round 4 is a short final challenge. Two quick matches appear in a row. Try it on your own.",
        "demo_round_4_prompt": "Press SPACE whenever a letter matches {n_value} steps back.",
        "demo_round_4_summary": "This is the same N-back rule you will use in the full game.",
        "demo_sliding_rule": "Example: {sequence} is a match because the last letter equals the letter {n_value} step(s) back. After that, the rule slides forward, so the next new letter is compared with {next_reference}, then the next one after that, and so on.",
    },
    "de": {
        "game_title": "Fokusspiel",
        "examiner_title": "Leitersteuerung",
        "waiting_for_examiner": "Warten auf die Aufsicht...",
        "participant_locked": "Der Teilnehmerbildschirm wird freigeschaltet, nachdem die Aufsicht die Sitzung bestaetigt hat.",
        "start_button": "Start",
        "examiner_heading": "Leitersteuerung",
        "examiner_subtitle": "Bitte Teilnehmerdaten eingeben und die Reihenfolge von Entspannung, Pause und Spiel festlegen, bevor der Teilnehmer startet.",
        "name": "Name",
        "participant_id": "ID",
        "age": "Alter",
        "n_value": "N-Wert",
        "relax_audio": "Alpha-Audio waehrend Entspannung abspielen",
        "note": "Notiz",
        "language": "Sprache",
        "session_planner": "Sitzungsplaner",
        "session": "Sitzung",
        "order": "Reihenfolge",
        "duration_minutes": "Dauer (Minuten)",
        "relax": "Entspannung",
        "break": "Pause",
        "game": "Spiel",
        "planner_help": "Verwenden Sie 1, 2 und 3 jeweils genau einmal. Eine Dauer von 0 ueberspringt die Stufe, aber Spiel muss groesser als 0 sein.",
        "awaiting_details": "Warte auf Sitzungsdaten.",
        "confirm_session": "Sitzung bestaetigen",
        "session_running_message": "Das Spiel laeuft bereits. Oeffnen Sie ein neues Spielfenster, wenn Sie eine weitere Sitzung moechten.",
        "name_required": "Name ist erforderlich.",
        "id_required": "ID ist erforderlich.",
        "age_required": "Alter ist erforderlich.",
        "n_value_required": "N-Wert ist erforderlich.",
        "n_value_integer": "Der N-Wert muss eine ganze Zahl sein.",
        "n_value_positive": "Der N-Wert muss mindestens 1 sein.",
        "session_confirmed_status": "Sitzung fuer {participant_name} bestaetigt.\nReihenfolge: {summary}\nBlockplan: {block_plan} ({data_source}).",
        "examiner_confirmed": "Die Sitzung wurde bestaetigt.",
        "participant_ready": "Teilnehmer: {participant_name}\nSitzungsreihenfolge: {summary}\nSprache: {language}\n\nDruecken Sie Start, um den gesamten Block zu beginnen.",
        "order_whole_number": "Die Reihenfolge fuer {stage} muss eine ganze Zahl sein.",
        "duration_number": "Die Dauer fuer {stage} muss eine Zahl sein.",
        "order_range": "Die Reihenfolge fuer {stage} muss 1, 2 oder 3 sein.",
        "duration_negative": "Die Dauer fuer {stage} darf nicht negativ sein.",
        "order_unique": "Entspannung, Pause und Spiel muessen 1, 2 und 3 jeweils genau einmal verwenden.",
        "game_duration_positive": "Die Spieldauer muss groesser als null sein.",
        "please_relax": "Bitte entspannen Sie sich, bis Sie das Signal hoeren",
        "please_break": "Bitte machen Sie eine Pause, bis Sie das Signal hoeren",
        "time_remaining": "Verbleibende Zeit: {minutes:02}:{seconds:02}",
        "preparing_next": "Naechste Sitzung wird vorbereitet...",
        "game_intro_title": "Spielphase",
        "game_intro_detail": "Sie beginnen gleich das Fokusspiel.\n\nDruecken Sie LEERTASTE, um durch die Anleitung zu gehen.",
        "how_to_play": "So wird gespielt",
        "how_to_play_detail": "Dies ist eine {n_value}-Back-Aufgabe.\n\nEs erscheinen nacheinander Buchstaben.\nDruecken Sie LEERTASTE nur dann, wenn der aktuelle Buchstabe mit dem Buchstaben vor {n_value} Schritt(en) uebereinstimmt.",
        "ready_to_start": "Bereit zum Start",
        "ready_to_start_detail": "Bleiben Sie fuer {duration:g} Minute(n) konzentriert.\n\nDruecken Sie LEERTASTE, wenn Sie bereit sind, das Spiel zu starten.",
        "block_ended": "Glueckwunsch, der Block ist beendet",
        "experiment_finished_saved": "Das Experiment ist beendet. Vielen Dank fuer Ihre Aufmerksamkeit!\n\nEndpunktzahl: {score:.2f}\n\nGespeichert: {filename}",
        "experiment_finished": "Das Experiment ist beendet. Vielen Dank fuer Ihre Aufmerksamkeit!\n\nEndpunktzahl: {score:.2f}",
        "launch_failed_title": "Fokusspiel",
        "launch_failed_message": "Das Spiel konnte nicht gestartet werden: {error}",
        "consent_title": "Einwilligung erforderlich",
        "consent_intro": "Bitte lesen Sie die Studienbedingungen unten und bestätigen Sie Ihre Einwilligung, bevor Sie das Spiel starten.",
        "consent_agree": "Ich stimme der Teilnahme an dieser EEG-Studie zu.",
        "consent_open_button": "Bedingungen lesen",
        "consent_prompt": "Bitte lesen Sie vor dem Start die Bedingungen und Einwilligung.",
        "demo_title": "Demo-Modus",
        "demo_intro_detail": "Diese gefuehrte Demo verwendet {n_value}-Back.\n\nSie spielen 4 kurze Uebungsrunden, die die Regel Schritt fuer Schritt vor dem echten Spiel erklaeren.\n\n{sliding_rule}",
        "demo_start": "Demo starten",
        "demo_round_title": "Demo-Runde {current}/{total}",
        "demo_play_round": "Runde spielen",
        "demo_next_round": "Naechste Runde",
        "demo_round_complete": "Runde beendet",
        "demo_complete_title": "Demo ist abgeschlossen",
        "demo_complete_detail": "Sie haben die gefuehrte Demo abgeschlossen.\n\nSie koennen die Demo erneut starten oder dieses Fenster schliessen.",
        "demo_restart": "Demo erneut starten",
        "demo_close": "Schliessen",
        "demo_feedback_perfect": "Sehr gut. Sie haben in dieser Runde korrekt reagiert.",
        "demo_feedback_missed": "Fast geschafft. Sie haben in dieser Runde mindestens einen notwendigen LEERTASTE-Druck verpasst.",
        "demo_feedback_extra": "Fast geschafft. Sie haben in dieser Runde LEERTASTE gedrueckt, obwohl kein Treffer vorlag.",
        "demo_feedback_mixed": "In dieser Runde gab es verpasste Treffer und zusaetzliche LEERTASTE-Drucke. Versuchen Sie die naechste Runde langsam.",
        "demo_round_1_intro": "Runde 1 erklaert die Grundregel. Merken Sie sich die ersten {n_value} Buchstaben. Druecken Sie bei dem letzten Buchstaben LEERTASTE, weil er mit dem ersten Buchstaben von vor {n_value} Schritten uebereinstimmt.",
        "demo_round_1_prompt": "Beobachten Sie die Buchstaben. Druecken Sie LEERTASTE nur beim letzten Buchstaben.",
        "demo_round_1_summary": "Der letzte Buchstabe entsprach dem ersten Buchstaben von vor {n_value} Schritten. Dann sollten Sie LEERTASTE druecken.",
        "demo_round_2_intro": "Runde 2 zeigt einen Nicht-Treffer. Druecken Sie beim letzten Buchstaben keine LEERTASTE, wenn er sich vom Buchstaben {n_value} Schritte zuvor unterscheidet.",
        "demo_round_2_prompt": "Druecken Sie LEERTASTE nur dann, wenn der neue Buchstabe {n_value} Schritte zurueck uebereinstimmt.",
        "demo_round_2_summary": "Der letzte Buchstabe stimmte nicht mit dem Buchstaben {n_value} Schritte zuvor ueberein, daher war keine Taste richtig.",
        "demo_round_3_intro": "Runde 3 mischt einen Treffer und einen Nicht-Treffer. Druecken Sie LEERTASTE nur dann, wenn der passende Buchstabe erscheint.",
        "demo_round_3_prompt": "Einer der neuen Buchstaben ist ein Treffer. Druecken Sie LEERTASTE nur fuer diesen.",
        "demo_round_3_summary": "Bei einem Treffer muessen Sie LEERTASTE druecken, bei einem Nicht-Treffer nicht.",
        "demo_round_4_intro": "Runde 4 ist eine kurze Abschlussuebung. Zwei schnelle Treffer erscheinen hintereinander. Probieren Sie es selbst.",
        "demo_round_4_prompt": "Druecken Sie LEERTASTE, wenn ein Buchstabe {n_value} Schritte zuvor uebereinstimmt.",
        "demo_round_4_summary": "Das ist genau dieselbe N-Back-Regel wie im echten Spiel.",
        "demo_sliding_rule": "Beispiel: {sequence} ist ein Treffer, weil der letzte Buchstabe dem Buchstaben von vor {n_value} Schritten entspricht. Danach verschiebt sich das Fenster nach vorn, also wird der naechste neue Buchstabe mit {next_reference} verglichen, dann mit dem darauffolgenden Buchstaben usw.",
    },
    "vi": {
        "game_title": "Trò chơi Tập trung",
        "examiner_title": "Điều khiển Giám sát",
        "waiting_for_examiner": "Đang chờ người giám sát...",
        "participant_locked": "Màn hình người chơi sẽ được mở sau khi người giám sát xác nhận phiên.",
        "start_button": "Bắt đầu",
        "examiner_heading": "Điều khiển Giám sát",
        "examiner_subtitle": "Nhập thông tin người tham gia và sắp xếp thứ tự Thư giãn, Nghỉ và Game trước khi người chơi bắt đầu.",
        "name": "Tên",
        "participant_id": "ID",
        "age": "Tuổi",
        "n_value": "Giá trị N",
        "relax_audio": "Phát âm thanh alpha trong lúc Thư giãn",
        "note": "Ghi chú",
        "language": "Ngôn ngữ",
        "session_planner": "Lập kế hoạch phiên",
        "session": "Phien",
        "order": "Thứ tự",
        "duration_minutes": "Thời lượng (phút)",
        "relax": "Thư giãn",
        "break": "Nghi",
        "game": "Game",
        "planner_help": "Sử dụng 1, 2 và 3, mỗi số chỉ một lần. Đặt thời lượng 0 để bỏ qua phần đó, nhưng Game phải lớn hơn 0.",
        "awaiting_details": "Đang chờ thông tin phiên.",
        "confirm_session": "Xác nhận phiên",
        "session_running_message": "Game đang chạy. Mở cửa sổ game mới nếu bạn muốn tạo phiên khác.",
        "name_required": "Cần nhập tên.",
        "id_required": "Cần nhập ID.",
        "age_required": "Cần nhập tuổi.",
        "n_value_required": "Cần nhập giá trị N.",
        "n_value_integer": "Giá trị N phải là số nguyên.",
        "n_value_positive": "Giá trị N phải lớn hơn hoặc bằng 1.",
        "session_confirmed_status": "Đã xác nhận phiên cho {participant_name}.\nThứ tự: {summary}\nKế hoạch block: {block_plan} ({data_source}).",
        "examiner_confirmed": "Đã xác nhận phiên.",
        "participant_ready": "Người tham gia: {participant_name}\nThứ tự phiên: {summary}\nNgôn ngữ: {language}\n\nNhấn Bắt đầu để chạy toàn bộ block.",
        "order_whole_number": "Thứ tự của {stage} phải là số nguyên.",
        "duration_number": "Thời lượng của {stage} phải là số.",
        "order_range": "Thứ tự của {stage} phải là 1, 2 hoặc 3.",
        "duration_negative": "Thời lượng của {stage} không được âm.",
        "order_unique": "Thư giãn, Nghỉ và Game phải dùng 1, 2 và 3, mỗi số một lần.",
        "game_duration_positive": "Thời lượng Game phải lớn hơn 0.",
        "please_relax": "Vui lòng thư giãn cho đến khi bạn nghe thấy âm thanh",
        "please_break": "Vui lòng nghỉ cho đến khi bạn nghe thấy âm thanh",
        "time_remaining": "Thời gian còn lại: {minutes:02}:{seconds:02}",
        "preparing_next": "Đang chuẩn bị phiên tiếp theo...",
        "game_intro_title": "Phiên Game",
        "game_intro_detail": "Bạn sắp bắt đầu Trò chơi Tập trung.\n\nNhấn SPACE để xem hướng dẫn.",
        "how_to_play": "Cách chơi",
        "how_to_play_detail": "Đây là bài tập {n_value}-back.\n\nCác chữ cái sẽ xuất hiện lần lượt.\nChỉ nhấn SPACE khi chữ cái hiện tại giống với chữ cái xuất hiện trước đó {n_value} bước.",
        "ready_to_start": "Sẵn sàng bắt đầu",
        "ready_to_start_detail": "Hãy tập trung trong {duration:g} phút.\n\nNhấn SPACE khi bạn sẵn sàng bắt đầu game.",
        "block_ended": "Chúc mừng, block đã kết thúc",
        "experiment_finished_saved": "Thí nghiệm đã kết thúc. Cảm ơn bạn đã chú ý!\n\nĐiểm cuối cùng: {score:.2f}\n\nĐã lưu: {filename}",
        "experiment_finished": "Thí nghiệm đã kết thúc. Cảm ơn bạn đã chú ý!\n\nĐiểm cuối cùng: {score:.2f}",
        "launch_failed_title": "Trò chơi Tập trung",
        "launch_failed_message": "Không thể khởi động game: {error}",
        "consent_title": "Yêu cầu đồng ý",
        "consent_intro": "Vui lòng đọc các điều khoản nghiên cứu bên dưới và xác nhận đồng ý trước khi bắt đầu game.",
        "consent_agree": "Tôi đồng ý tham gia nghiên cứu EEG này.",
        "consent_open_button": "Điều khoản và điều kiện",
        "consent_prompt": "Vui lòng đọc điều khoản và điều kiện trước khi bắt đầu game.",
        "demo_title": "Chế độ Demo",
        "demo_intro_detail": "Demo có hướng dẫn này dùng mức {n_value}-back.\n\nBạn sẽ chơi 4 vòng ngắn để hiểu luật từng bước trước khi vào game thật.\n\n{sliding_rule}",
        "demo_start": "Bắt đầu demo",
        "demo_round_title": "Vòng demo {current}/{total}",
        "demo_play_round": "Chơi vòng này",
        "demo_next_round": "Vòng tiếp theo",
        "demo_round_complete": "Đã xong vòng này",
        "demo_complete_title": "Demo đã hoàn thành",
        "demo_complete_detail": "Bạn đã hoàn thành phần demo có hướng dẫn.\n\nBạn có thể chạy lại demo hoặc đóng cửa sổ này.",
        "demo_restart": "Chạy lại demo",
        "demo_close": "Đóng",
        "demo_feedback_perfect": "Rất tốt. Bạn đã phản hồi đúng trong vòng này.",
        "demo_feedback_missed": "Gần đúng rồi. Bạn đã bỏ lỡ ít nhất một lần cần nhấn SPACE trong vòng này.",
        "demo_feedback_extra": "Gần đúng rồi. Bạn đã nhấn SPACE khi không có ký tự khớp trong vòng này.",
        "demo_feedback_mixed": "Vòng này có cả lần bỏ lỡ ký tự khớp và lần nhấn dư. Hãy thử vòng tiếp theo chậm hơn.",
        "demo_round_1_intro": "Vòng 1 giúp bạn hiểu luật cơ bản. Với {n_value} ký tự đầu tiên, chỉ cần ghi nhớ. Ở ký tự cuối, hãy nhấn SPACE vì nó giống ký tự đầu tiên xuất hiện trước đó {n_value} bước.",
        "demo_round_1_prompt": "Quan sát các ký tự. Chỉ nhấn SPACE ở ký tự cuối cùng.",
        "demo_round_1_summary": "Ký tự cuối cùng giống ký tự đầu tiên từ {n_value} bước trước. Đó là lúc bạn nên nhấn SPACE.",
        "demo_round_2_intro": "Vòng 2 cho bạn thấy trường hợp không khớp. Đừng nhấn SPACE ở ký tự cuối nếu nó khác ký tự xuất hiện trước đó {n_value} bước.",
        "demo_round_2_prompt": "Đừng nhấn SPACE nếu ký tự mới không khớp với {n_value} bước trước.",
        "demo_round_2_summary": "Ký tự cuối không khớp với ký tự {n_value} bước trước, nên thao tác đúng là không nhấn phím.",
        "demo_round_3_intro": "Vòng 3 có một ký tự khớp và một ký tự không khớp. Chỉ nhấn SPACE khi ký tự khớp xuất hiện.",
        "demo_round_3_prompt": "Một trong các ký tự mới là ký tự khớp. Chỉ nhấn SPACE cho ký tự đó.",
        "demo_round_3_summary": "Ký tự khớp cần nhấn SPACE, còn ký tự không khớp thì không nhấn.",
        "demo_round_4_intro": "Vòng 4 là thử thách ngắn cuối cùng. Hai ký tự khớp xuất hiện liên tiếp. Hãy tự thử nhé.",
        "demo_round_4_prompt": "Nhấn SPACE khi ký tự hiện tại khớp với ký tự {n_value} bước trước.",
        "demo_round_4_summary": "Đây chính là luật N-back bạn sẽ dùng trong game thật.",
        "demo_sliding_rule": "Ví dụ: {sequence} là một lần khớp vì ký tự cuối cùng giống ký tự ở {n_value} bước trước. Sau đó cửa sổ so sánh sẽ trượt lên phía trước, nên ký tự mới tiếp theo sẽ được so với {next_reference}, rồi tiếp tục so với ký tự tiếp theo sau đó.",
    },
}


class NBackGameController:
    def __init__(self, root: tk.Tk, assets_dir: Path) -> None:
        self.root = root
        self.assets_dir = assets_dir
        self.relax_audio_path = assets_dir.parent.parent / "alpha_15m.mp3"
        self.language_code = self._resolve_language(os.environ.get("EEG_GAME_LANGUAGE", "en"))
        self.demo_mode = self._coerce_bool(os.environ.get("EEG_GAME_DEMO_MODE", False))
        self.demo_n_value = self._coerce_positive_int(os.environ.get("EEG_GAME_DEMO_N", 3), default=3)
        self.root.attributes("-fullscreen", True)
        self.root.title(self._t("game_title"))
        self.root.configure(bg="#111827")

        self.rules: NBackRules = load_rules(assets_dir / "rules.txt")
        self.participant_task_data = load_participant_tasks(assets_dir / "participant-task.csv")
        self.total_blocks = 5
        self.master_control_path = assets_dir.parent.parent / "EEG_APP" / "Master_Control.xlsx"
        ensure_master_control_workbook(self.master_control_path)

        self.session: ExaminerSession | None = None
        self.session_ready = False
        self.session_started = False
        self.current_block = 1
        self.n: int | None = None
        self.sequence: list[str] = []
        self.results: list[TrialResult] = []
        self.completed_blocks: list[tuple[int, int, list[TrialResult]]] = []
        self.is_playing = False
        self.current_letter: str | None = None
        self.current_instruction_screen = 0
        self.state = "waiting"
        self.experiment_start_time: str | None = None
        self.date_experiment: str | None = None
        self.current_stage_index = -1
        self.current_stage_duration_minutes = 0.0
        self.current_game_duration_minutes = float(self.rules.actual_minutes)
        self.session_export_path: Path | None = None
        self.game_stage_completed = False
        self.current_game_n_value: int | None = None
        self.game_intro_pages: list[tuple[str, str]] = []
        self.countdown_after_id: str | None = None
        self.stage_transition_after_id: str | None = None
        self.letter_hide_after_id: str | None = None
        self.next_letter_after_id: str | None = None
        self.reset_color_after_id: str | None = None
        self.second_beep_after_id: str | None = None
        self.relax_audio_thread: threading.Thread | None = None
        self.relax_audio_stop_event = threading.Event()
        self.relax_audio_process: subprocess.Popen[str] | None = None
        self.demo_steps: list[dict[str, object]] = []
        self.demo_step_index = 0
        self.demo_round_prompt = ""
        self.max_actual_task_trial_number = self._calculate_game_trials(self.current_game_duration_minutes)
        self.max_practice_task_trial_number = calculate_trial_count(
            self.rules.practice_minutes,
            self.rules.display_time_ms,
            self.rules.intertrial_interval_ms,
        )
        self.demo_display_time_ms = max(self.rules.display_time_ms, 1400)
        self.demo_intertrial_interval_ms = max(self.rules.intertrial_interval_ms, 850)

        self.status_label = tk.Label(
            root,
            text=self._t("waiting_for_examiner"),
            font=("Arial", 36, "bold"),
            fg="#F9FAFB",
            bg="#111827",
            justify="center",
            wraplength=1100,
        )
        self.status_label.pack(expand=True, fill="both", padx=40, pady=(80, 16))

        self.detail_label = tk.Label(
            root,
            text=self._t("participant_locked"),
            font=("Arial", 20),
            fg="#9CA3AF",
            bg="#111827",
            justify="center",
            wraplength=1000,
        )
        self.detail_label.pack(padx=40, pady=(0, 24))

        self.start_button = tk.Button(
            root,
            text=self._t("start_button"),
            command=self.begin_session,
            font=("Arial", 24, "bold"),
            bg="#14B8A6",
            fg="#06202A",
            activebackground="#0D9488",
            activeforeground="#ECFEFF",
            relief=tk.FLAT,
            padx=24,
            pady=12,
        )
        self.start_button.config(state=tk.DISABLED)
        self.start_button.pack_forget()

        self.secondary_action_button = tk.Button(
            root,
            font=("Arial", 18, "bold"),
            bg="#334155",
            fg="#F8FAFC",
            activebackground="#1E293B",
            activeforeground="#F8FAFC",
            relief=tk.FLAT,
            padx=22,
            pady=10,
        )
        self.secondary_action_button.pack_forget()

        self.consent_accepted_var = tk.BooleanVar(value=False)
        self.consent_window: tk.Toplevel | None = None
        self.consent_container = tk.Frame(root, bg="#111827", highlightbackground="#334155", highlightthickness=1)
        self.consent_title_label = tk.Label(
            self.consent_container,
            text=self._t("consent_title"),
            font=("Arial", 20, "bold"),
            fg="#F8FAFC",
            bg="#111827",
            anchor="w",
        )
        self.consent_title_label.pack(fill="x", padx=24, pady=(20, 6))
        self.consent_intro_label = tk.Label(
            self.consent_container,
            text=self._t("consent_prompt"),
            font=("Arial", 14, "bold"),
            fg="#F8FAFC",
            bg="#111827",
            justify="left",
            wraplength=980,
            anchor="w",
        )
        self.consent_intro_label.pack(fill="x", padx=24, pady=(0, 14))
        self.consent_link_button = tk.Label(
            self.consent_container,
            text=self._t("consent_open_button"),
            font=("Arial", 13, "bold"),
            bg="#16A34A",
            fg="#F8FAFC",
            padx=20,
            pady=12,
            cursor="hand2",
            relief=tk.FLAT,
            bd=0,
        )
        self.consent_link_button.pack(anchor="w", padx=24, pady=(0, 16))
        self.consent_link_button.bind("<Button-1>", lambda _event: self._open_consent_window())
        self.consent_link_button.bind("<Enter>", lambda _event: self.consent_link_button.config(bg="#15803D"))
        self.consent_link_button.bind("<Leave>", lambda _event: self.consent_link_button.config(bg="#16A34A"))

        self.consent_checkbox = tk.Checkbutton(
            self.consent_container,
            text=self._t("consent_agree"),
            variable=self.consent_accepted_var,
            command=self._update_start_gate,
            font=("Arial", 12, "bold"),
            fg="#F8FAFC",
            bg="#111827",
            activebackground="#111827",
            activeforeground="#ECFEFF",
            selectcolor="#166534",
            anchor="w",
        )
        self.consent_checkbox.pack(fill="x", padx=24, pady=(0, 18))

        self.root.bind("<space>", self.on_space_press)
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)
        self.examiner_window: tk.Toplevel | None = None
        preset_session = self._load_preset_session()
        if self.demo_mode:
            self._setup_demo_mode()
        elif preset_session is not None:
            self._apply_session(preset_session, source_label="codex setup")
        else:
            self.examiner_window = tk.Toplevel(self.root)
            self.examiner_window.title(self._t("examiner_title"))
            self.examiner_window.configure(bg="#F8FAFC")
            self.examiner_window.geometry("680x800")
            self.examiner_window.minsize(640, 760)
            self.examiner_window.protocol("WM_DELETE_WINDOW", self._on_examiner_close)
            self._build_examiner_window()

    def _set_message_layout(self, *, compact: bool) -> None:
        if compact:
            self.status_label.pack_configure(expand=False, fill="none", pady=(140, 12))
            self.detail_label.pack_configure(pady=(0, 18))
        else:
            self.status_label.pack_configure(expand=True, fill="both", pady=(80, 16))
            self.detail_label.pack_configure(pady=(0, 24))

    def _show_primary_action(self, text: str, command) -> None:
        self.start_button.config(text=text, command=command, state=tk.NORMAL)
        self.start_button.pack(pady=(0, 18))

    def _hide_primary_action(self) -> None:
        self.start_button.pack_forget()

    def _show_secondary_action(self, text: str, command) -> None:
        self.secondary_action_button.config(text=text, command=command)
        self.secondary_action_button.pack(pady=(0, 48))

    def _hide_secondary_action(self) -> None:
        self.secondary_action_button.pack_forget()

    def _setup_demo_mode(self) -> None:
        self.consent_container.pack_forget()
        self._hide_secondary_action()
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("demo_title"), font=("Arial", 42, "bold"))
        self.detail_label.config(
            text=self._t(
                "demo_intro_detail",
                n_value=self.demo_n_value,
                sliding_rule=self._demo_sliding_rule_text(self.demo_n_value),
            )
        )
        self._show_primary_action(self._t("demo_start"), self._begin_demo_cycle)

    def _build_examiner_window(self) -> None:
        container = tk.Frame(self.examiner_window, bg="#F8FAFC")
        container.pack(fill="both", expand=True, padx=26, pady=26)

        title = tk.Label(
            container,
            text=self._t("examiner_heading"),
            font=("Arial", 26, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            container,
            text=self._t("examiner_subtitle"),
            font=("Arial", 12),
            fg="#475569",
            bg="#F8FAFC",
            wraplength=600,
            justify="left",
        )
        subtitle.pack(anchor="w", pady=(8, 18))

        form_card = tk.Frame(container, bg="#FFFFFF", highlightbackground="#D9E2EC", highlightthickness=1)
        form_card.pack(fill="x", pady=(0, 16))

        form = tk.Frame(form_card, bg="#FFFFFF")
        form.pack(fill="x", padx=18, pady=18)

        self.examiner_fields: dict[str, tk.Entry | tk.Text] = {}
        field_specs = [
            ("participant_name", self._t("name")),
            ("participant_id", self._t("participant_id")),
            ("age", self._t("age")),
            ("n_value", self._t("n_value")),
        ]
        for row_index, (key, label_text) in enumerate(field_specs):
            label = tk.Label(form, text=label_text, font=("Arial", 12, "bold"), fg="#1E293B", bg="#FFFFFF")
            label.grid(row=row_index, column=0, sticky="w", pady=8)
            entry = tk.Entry(form, font=("Arial", 12), width=28, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            entry.grid(row=row_index, column=1, sticky="ew", pady=8, padx=(16, 0), ipady=8)
            if key == "n_value":
                entry.insert(0, "3")
            self.examiner_fields[key] = entry

        note_label = tk.Label(form, text=self._t("note"), font=("Arial", 12, "bold"), fg="#1E293B", bg="#FFFFFF")
        note_label.grid(row=len(field_specs), column=0, sticky="nw", pady=8)
        note_box = tk.Text(form, font=("Arial", 12), width=28, height=4, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
        note_box.grid(row=len(field_specs), column=1, sticky="ew", pady=8, padx=(16, 0))
        self.examiner_fields["note"] = note_box

        self.relax_audio_var = tk.BooleanVar(value=False)
        relax_audio_label = tk.Label(
            form,
            text=self._t("relax_audio"),
            font=("Arial", 12, "bold"),
            fg="#1E293B",
            bg="#FFFFFF",
        )
        relax_audio_label.grid(row=len(field_specs) + 1, column=0, sticky="w", pady=8)
        relax_audio_checkbox = tk.Checkbutton(
            form,
            variable=self.relax_audio_var,
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            selectcolor="#D1FAE5",
        )
        relax_audio_checkbox.grid(row=len(field_specs) + 1, column=1, sticky="w", pady=8, padx=(16, 0))

        language_label = tk.Label(form, text=self._t("language"), font=("Arial", 12, "bold"), fg="#1E293B", bg="#FFFFFF")
        language_label.grid(row=len(field_specs) + 2, column=0, sticky="w", pady=8)
        self.language_value_label = tk.Label(
            form,
            text=LANGUAGE_LABELS.get(self.language_code, self.language_code),
            font=("Arial", 12),
            fg="#0F172A",
            bg="#FFFFFF",
            anchor="w",
        )
        self.language_value_label.grid(row=len(field_specs) + 2, column=1, sticky="ew", pady=8, padx=(16, 0))
        form.grid_columnconfigure(1, weight=1)

        planner_card = tk.Frame(container, bg="#FFFFFF", highlightbackground="#D9E2EC", highlightthickness=1)
        planner_card.pack(fill="x", pady=(0, 16))

        planner = tk.Frame(planner_card, bg="#FFFFFF")
        planner.pack(fill="x", padx=18, pady=18)

        planner_title = tk.Label(
            planner,
            text=self._t("session_planner"),
            font=("Arial", 16, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        planner.grid_columnconfigure(2, weight=1)
        planner_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        headers = [(self._t("session"), 0), (self._t("order"), 1), (self._t("duration_minutes"), 2)]
        for text, column in headers:
            tk.Label(planner, text=text, font=("Arial", 11, "bold"), fg="#475569", bg="#FFFFFF").grid(
                row=1, column=column, sticky="w", pady=(0, 8), padx=(0, 12)
            )

        default_stages = [
            (self._t("relax"), 1, 2.0),
            (self._t("break"), 2, 2.0),
            (self._t("game"), 3, float(self.rules.actual_minutes)),
        ]
        self.stage_fields: dict[str, dict[str, tk.Entry]] = {}
        for row_index, (kind, order, duration) in enumerate(default_stages, start=2):
            tk.Label(planner, text=kind, font=("Arial", 12, "bold"), fg="#111827", bg="#FFFFFF").grid(
                row=row_index, column=0, sticky="w", pady=8
            )
            order_entry = tk.Entry(planner, font=("Arial", 12), width=8, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            order_entry.insert(0, str(order))
            order_entry.grid(row=row_index, column=1, sticky="w", pady=8, padx=(0, 12), ipady=8)
            duration_entry = tk.Entry(planner, font=("Arial", 12), width=12, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            duration_entry.insert(0, f"{duration:g}")
            duration_entry.grid(row=row_index, column=2, sticky="ew", pady=8, ipady=8)
            self.stage_fields[kind.lower() if kind.lower() in {"relax", "break", "game"} else self._stage_key(kind)] = {
                "order": order_entry,
                "duration": duration_entry,
            }

        if "relax" not in self.stage_fields:
            self.stage_fields = {
                "relax": self.stage_fields[self._stage_key(self._t("relax"))],
                "break": self.stage_fields[self._stage_key(self._t("break"))],
                "game": self.stage_fields[self._stage_key(self._t("game"))],
            }

        help_text = tk.Label(
            planner,
            text=self._t("planner_help"),
            font=("Arial", 11),
            fg="#64748B",
            bg="#FFFFFF",
            wraplength=580,
            justify="left",
        )
        help_text.grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 0))

        self.examiner_status_label = tk.Label(
            container,
            text=self._t("awaiting_details"),
            font=("Arial", 12),
            fg="#64748B",
            bg="#F8FAFC",
            justify="left",
            wraplength=620,
        )
        self.examiner_status_label.pack(fill="x", pady=(0, 18))

        footer = tk.Frame(container, bg="#F8FAFC")
        footer.pack(fill="x", side="bottom")

        self.confirm_button = tk.Button(
            footer,
            text=self._t("confirm_session"),
            command=self.confirm_examiner_session,
            font=("Arial", 15, "bold"),
            bg="#2563EB",
            fg="#F8FAFC",
            activebackground="#1D4ED8",
            activeforeground="#F8FAFC",
            relief=tk.FLAT,
            padx=16,
            pady=12,
        )
        self.confirm_button.pack(fill="x")

    def _on_examiner_close(self) -> None:
        if self.examiner_window is not None:
            self.examiner_window.withdraw()

    def _open_consent_window(self) -> None:
        if self.consent_window is not None and self.consent_window.winfo_exists():
            self.consent_window.lift()
            self.consent_window.focus_force()
            return

        self.consent_window = tk.Toplevel(self.root)
        self.consent_window.title(self._t("consent_title"))
        self.consent_window.configure(bg="#F8FAFC")
        self.consent_window.geometry("680x560")
        self.consent_window.minsize(520, 420)
        self.consent_window.resizable(True, True)
        self.consent_window.attributes("-fullscreen", False)
        self.consent_window.protocol("WM_DELETE_WINDOW", self.consent_window.destroy)

        container = tk.Frame(self.consent_window, bg="#F8FAFC")
        container.pack(fill="both", expand=True, padx=18, pady=18)

        title = tk.Label(
            container,
            text=self._t("consent_title"),
            font=("Arial", 20, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        title.pack(anchor="w")

        intro = tk.Label(
            container,
            text=self._t("consent_intro"),
            font=("Arial", 13),
            fg="#475569",
            bg="#F8FAFC",
            justify="left",
            wraplength=620,
        )
        intro.pack(anchor="w", pady=(8, 12))

        text_frame = tk.Frame(container, bg="#F8FAFC")
        text_frame.pack(fill="both", expand=True)
        consent_text = tk.Text(
            text_frame,
            font=("Arial", 14),
            wrap="word",
            bg="#FFFFFF",
            fg="#111827",
            relief=tk.FLAT,
            padx=14,
            pady=14,
        )
        consent_text.insert("1.0", CONSENT_TEXT.get(self.language_code, CONSENT_TEXT["en"]))
        consent_text.config(state=tk.DISABLED)
        scrollbar = tk.Scrollbar(text_frame, command=consent_text.yview)
        consent_text.configure(yscrollcommand=scrollbar.set)
        consent_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def confirm_examiner_session(self) -> None:
        if self.session_started:
            messagebox.showinfo(self._t("examiner_title"), self._t("session_running_message"))
            return

        participant_name = self._entry_value("participant_name")
        participant_id = self._entry_value("participant_id")
        age = self._entry_value("age")
        n_value_text = self._entry_value("n_value")
        note = self._entry_value("note")

        if not participant_name:
            messagebox.showerror(self._t("examiner_title"), self._t("name_required"))
            return
        if not participant_id:
            messagebox.showerror(self._t("examiner_title"), self._t("id_required"))
            return
        if not age:
            messagebox.showerror(self._t("examiner_title"), self._t("age_required"))
            return
        if not n_value_text:
            messagebox.showerror(self._t("examiner_title"), self._t("n_value_required"))
            return
        try:
            n_value = int(n_value_text)
        except ValueError:
            messagebox.showerror(self._t("examiner_title"), self._t("n_value_integer"))
            return
        if n_value < 1:
            messagebox.showerror(self._t("examiner_title"), self._t("n_value_positive"))
            return

        stage_plan = self._read_stage_plan()
        if stage_plan is None:
            return

        block_plan = resolve_block_plan(participant_id, self.participant_task_data, self.total_blocks)
        self._apply_session(
            ExaminerSession(
                participant_name=participant_name,
                participant_id=participant_id,
                age=age,
                n_value=n_value,
                relax_audio_enabled=self.relax_audio_var.get(),
                note=note,
                block_plan=block_plan,
                session_stages=stage_plan,
            ),
            source_label=(
                "participant-task.csv"
                if participant_id.isdigit() and int(participant_id) in self.participant_task_data
                else "generated fallback"
            ),
        )

    def _apply_session(self, session: ExaminerSession, source_label: str) -> None:
        self.session = session
        self.session_ready = True
        self.session_started = False
        self.current_stage_index = -1
        self.current_block = 1
        self.completed_blocks.clear()
        self.results.clear()
        self.sequence.clear()
        self.session_export_path = None
        self.game_stage_completed = False
        self.current_game_n_value = session.n_value

        summary = " -> ".join(
            f"{self._stage_name(stage.kind)} ({stage.duration_minutes:g} min)"
            for stage in session.session_stages
        )
        if hasattr(self, "examiner_status_label"):
            self.examiner_status_label.config(
                text=self._t(
                    "session_confirmed_status",
                    participant_name=session.participant_name,
                    summary=summary,
                    block_plan=", ".join(str(value) for value in session.block_plan),
                    data_source=source_label,
                ),
                fg="#0F766E",
            )
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("examiner_confirmed"))
        self.detail_label.config(
            text=self._t(
                "participant_ready",
                participant_name=session.participant_name,
                summary=summary,
                language=LANGUAGE_LABELS.get(self.language_code, self.language_code),
            )
        )
        self.consent_accepted_var.set(False)
        self.consent_title_label.config(text=self._t("consent_title"))
        self.consent_intro_label.config(text=self._t("consent_prompt"))
        self.consent_link_button.config(text=self._t("consent_open_button"))
        self.consent_checkbox.config(text=self._t("consent_agree"))
        self.consent_container.pack(fill="both", expand=False, padx=80, pady=(0, 24))
        self.start_button.config(text=self._t("start_button"))
        self.start_button.pack(pady=(0, 48))
        self._hide_secondary_action()
        self._update_start_gate()

    def _update_start_gate(self) -> None:
        self.start_button.config(state=tk.NORMAL if self.consent_accepted_var.get() else tk.DISABLED)

    def _load_preset_session(self) -> ExaminerSession | None:
        raw = os.environ.get("EEG_GAME_SESSION_JSON")
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None

        participant_name = str(payload.get("participant_name", "")).strip()
        participant_id = str(payload.get("participant_id", "")).strip()
        age = str(payload.get("age", "")).strip()
        try:
            n_value = int(payload.get("n_value", 3))
        except (TypeError, ValueError):
            return None
        if not participant_name or not participant_id or not age or n_value < 1:
            return None
        relax_audio_enabled = self._coerce_bool(payload.get("relax_audio_enabled", False))
        block_plan = resolve_block_plan(participant_id, self.participant_task_data, self.total_blocks)
        stage_payload = payload.get("session_stages", [])
        stages = [
            SessionStage(
                kind=str(stage["kind"]),
                duration_minutes=float(stage["duration_minutes"]),
                order=int(stage["order"]),
            )
            for stage in stage_payload
            if float(stage["duration_minutes"]) > 0
        ]
        if not stages:
            return None
        stages = sorted(stages, key=lambda stage: stage.order)
        return ExaminerSession(
            participant_name=participant_name,
            participant_id=participant_id,
            age=age,
            n_value=n_value,
            relax_audio_enabled=relax_audio_enabled,
            note=str(payload.get("note", "")).strip(),
            block_plan=block_plan,
            session_stages=stages,
        )

    def _read_stage_plan(self) -> list[SessionStage] | None:
        stages: list[SessionStage] = []
        orders: list[int] = []
        for kind in ("relax", "break", "game"):
            order_text = self.stage_fields[kind]["order"].get().strip()
            duration_text = self.stage_fields[kind]["duration"].get().strip()
            try:
                order = int(order_text)
            except ValueError:
                messagebox.showerror(self._t("examiner_title"), self._t("order_whole_number", stage=self._stage_name(kind)))
                return None
            try:
                duration = float(duration_text)
            except ValueError:
                messagebox.showerror(self._t("examiner_title"), self._t("duration_number", stage=self._stage_name(kind)))
                return None
            if order not in (1, 2, 3):
                messagebox.showerror(self._t("examiner_title"), self._t("order_range", stage=self._stage_name(kind)))
                return None
            if duration < 0:
                messagebox.showerror(self._t("examiner_title"), self._t("duration_negative", stage=self._stage_name(kind)))
                return None
            orders.append(order)
            stages.append(SessionStage(kind=kind, duration_minutes=duration, order=order))

        if sorted(orders) != [1, 2, 3]:
            messagebox.showerror(self._t("examiner_title"), self._t("order_unique"))
            return None

        game_stage = next(stage for stage in stages if stage.kind == "game")
        if game_stage.duration_minutes <= 0:
            messagebox.showerror(self._t("examiner_title"), self._t("game_duration_positive"))
            return None

        return sorted((stage for stage in stages if stage.duration_minutes > 0), key=lambda stage: stage.order)

    def begin_session(self) -> None:
        if not self.session_ready or self.session is None or not self.consent_accepted_var.get():
            return
        self._clear_runtime_callbacks()
        self._stop_relax_audio()
        self.session_started = True
        self.current_stage_index = -1
        self.completed_blocks.clear()
        self.results.clear()
        self.sequence.clear()
        self.session_export_path = None
        self.game_stage_completed = False
        self.current_game_n_value = self.session.n_value if self.session else 3
        self.consent_container.pack_forget()
        self.start_button.pack_forget()
        self.experiment_start_time = datetime.now().strftime("%H:%M:%S")
        self.date_experiment = date.today().strftime("%d/%m/%Y")
        self._emit_command("START_RECORDING")
        self._advance_to_next_stage()

    def _advance_to_next_stage(self) -> None:
        if self.session is None:
            return
        self._stop_relax_audio()
        self.stage_transition_after_id = None
        self.current_stage_index += 1
        if self.current_stage_index >= len(self.session.session_stages):
            self.finish_session()
            return

        stage = self.session.session_stages[self.current_stage_index]
        self.current_stage_duration_minutes = stage.duration_minutes
        self.root.configure(bg="#111827")
        if stage.kind == "game":
            self._show_game_intro(stage.duration_minutes)
            return
        self._start_guided_stage(stage.kind, stage.duration_minutes)

    def _start_guided_stage(self, kind: str, duration_minutes: float) -> None:
        self._cancel_after("countdown_after_id")
        self._cancel_after("letter_hide_after_id")
        self._cancel_after("next_letter_after_id")
        self._stop_relax_audio()
        self.is_playing = False
        self.state = kind
        self._set_message_layout(compact=False)
        total_seconds = max(1, int(round(duration_minutes * 60)))
        if kind == "relax":
            self.status_label.config(text=self._t("please_relax"))
            if self.session is not None and self.session.relax_audio_enabled:
                self._start_relax_audio()
        else:
            self.status_label.config(text=self._t("please_break"))
        self.detail_label.config(text="")
        self._run_stage_countdown(total_seconds)

    def _run_stage_countdown(self, remaining_seconds: int) -> None:
        if self.state not in {"relax", "break"}:
            return
        minutes, seconds = divmod(remaining_seconds, 60)
        self.detail_label.config(text=self._t("time_remaining", minutes=minutes, seconds=seconds))
        if remaining_seconds <= 0:
            self._stop_relax_audio()
            self._play_stage_end_signal()
            self.detail_label.config(text=self._t("preparing_next"))
            self.stage_transition_after_id = self.root.after(1000, self._advance_to_next_stage)
            return
        self.countdown_after_id = self.root.after(1000, self._run_stage_countdown, remaining_seconds - 1)

    def _start_game_stage(self, duration_minutes: float) -> None:
        self._stop_relax_audio()
        self._cancel_after("countdown_after_id")
        self._cancel_after("stage_transition_after_id")
        self.current_game_duration_minutes = duration_minutes
        self.max_actual_task_trial_number = self._calculate_game_trials(duration_minutes)
        self.current_block = 1
        self.results.clear()
        self.sequence.clear()
        self.n = self.current_game_n_value if self.current_game_n_value is not None else 1
        self.state = "playing"
        self.is_playing = True
        self._set_message_layout(compact=False)
        self.sequence = self.generate_sequence(self.max_actual_task_trial_number)
        self.show_next_letter()

    def on_space_press(self, _event) -> None:
        if self.state == "game_intro":
            self._advance_game_intro()
            return
        if self.state in {"playing", "demo_playing"}:
            self.check_match()

    def _show_game_intro(self, duration_minutes: float) -> None:
        self._stop_relax_audio()
        self._cancel_after("countdown_after_id")
        self._cancel_after("stage_transition_after_id")
        self.state = "game_intro"
        self.is_playing = False
        self.current_game_duration_minutes = duration_minutes
        n_value = self.current_game_n_value if self.current_game_n_value is not None else 1
        self.current_instruction_screen = 0
        self.game_intro_pages = [
            (self._t("game_intro_title"), self._t("game_intro_detail")),
            (self._t("how_to_play"), self._t("how_to_play_detail", n_value=n_value)),
            (self._t("ready_to_start"), self._t("ready_to_start_detail", duration=duration_minutes)),
        ]
        self._render_game_intro_page()

    def _render_game_intro_page(self) -> None:
        if not self.game_intro_pages:
            return
        title, detail = self.game_intro_pages[self.current_instruction_screen]
        self._set_message_layout(compact=True)
        self.status_label.config(text=title, font=("Arial", 40, "bold"))
        self.detail_label.config(text=detail)
        self.root.configure(bg="#111827")

    def _advance_game_intro(self) -> None:
        if self.state != "game_intro":
            return
        self.current_instruction_screen += 1
        if self.current_instruction_screen >= len(self.game_intro_pages):
            self._start_game_stage(self.current_game_duration_minutes)
            return
        self._render_game_intro_page()

    def _begin_demo_cycle(self) -> None:
        self._clear_runtime_callbacks()
        self._stop_relax_audio()
        self.root.configure(bg="#111827")
        self.current_game_n_value = self.demo_n_value
        self.demo_steps = self._build_demo_steps(self.demo_n_value)
        self.demo_step_index = 0
        self._show_demo_step_intro()

    def _show_demo_step_intro(self) -> None:
        if not self.demo_steps:
            self._show_demo_complete()
            return
        step = self.demo_steps[self.demo_step_index]
        self.state = "demo_intro"
        self.is_playing = False
        self._set_message_layout(compact=True)
        self.status_label.config(
            text=self._t("demo_round_title", current=self.demo_step_index + 1, total=len(self.demo_steps)),
            font=("Arial", 40, "bold"),
        )
        self.detail_label.config(text=str(step["intro"]))
        self._hide_secondary_action()
        self._show_primary_action(self._t("demo_play_round"), self._start_demo_round)

    def _start_demo_round(self) -> None:
        step = self.demo_steps[self.demo_step_index]
        self._clear_runtime_callbacks()
        self.root.configure(bg="#111827")
        self.n = self.demo_n_value
        self.sequence = list(step["sequence"])
        self.results.clear()
        self.current_letter = None
        self.demo_round_prompt = str(step["prompt"])
        self.state = "demo_playing"
        self.is_playing = True
        self._set_message_layout(compact=False)
        self.status_label.config(text="", font=("Arial", 120, "bold"))
        self.detail_label.config(text=self.demo_round_prompt)
        self._hide_primary_action()
        self._hide_secondary_action()
        self.show_next_letter()

    def _complete_demo_round(self) -> None:
        self._cancel_after("letter_hide_after_id")
        self._cancel_after("next_letter_after_id")
        self.is_playing = False
        self.state = "demo_result"
        step = self.demo_steps[self.demo_step_index]
        feedback_key = self._demo_feedback_key()
        detail = f"{step['summary']}\n\n{self._t(feedback_key)}"
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("demo_round_complete"), font=("Arial", 38, "bold"))
        self.detail_label.config(text=detail)
        if self.demo_step_index >= len(self.demo_steps) - 1:
            self._show_primary_action(self._t("demo_restart"), self._begin_demo_cycle)
            self._show_secondary_action(self._t("demo_close"), self._on_root_close)
            self.status_label.config(text=self._t("demo_complete_title"), font=("Arial", 38, "bold"))
            self.detail_label.config(text=self._t("demo_complete_detail") + "\n\n" + detail)
            return
        self._show_primary_action(self._t("demo_next_round"), self._advance_demo_step)

    def _advance_demo_step(self) -> None:
        self.demo_step_index += 1
        if self.demo_step_index >= len(self.demo_steps):
            self._show_demo_complete()
            return
        self._show_demo_step_intro()

    def _show_demo_complete(self) -> None:
        self.state = "demo_complete"
        self.is_playing = False
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("demo_complete_title"), font=("Arial", 40, "bold"))
        self.detail_label.config(text=self._t("demo_complete_detail"))
        self._show_primary_action(self._t("demo_restart"), self._begin_demo_cycle)
        self._show_secondary_action(self._t("demo_close"), self._on_root_close)

    def _build_demo_steps(self, n_value: int) -> list[dict[str, object]]:
        alphabet = [chr(index) for index in range(65, 91)]

        def base_letters(offset: int) -> list[str]:
            return [alphabet[(offset + index) % len(alphabet)] for index in range(n_value)]

        round_one = base_letters(0)
        round_two = base_letters(6)
        round_three = base_letters(12)
        round_four = base_letters(18)

        nonmatch_two = alphabet[(6 + n_value) % len(alphabet)]
        if nonmatch_two == round_two[0]:
            nonmatch_two = alphabet[(7 + n_value) % len(alphabet)]

        nonmatch_three = alphabet[(12 + n_value + 1) % len(alphabet)]
        if nonmatch_three == round_three[1 % len(round_three)]:
            nonmatch_three = alphabet[(12 + n_value + 2) % len(alphabet)]

        return [
            {
                "intro": self._t("demo_round_1_intro", n_value=n_value),
                "prompt": self._t("demo_round_1_prompt"),
                "summary": self._t("demo_round_1_summary", n_value=n_value),
                "sequence": round_one + [round_one[0]],
            },
            {
                "intro": self._t("demo_round_2_intro", n_value=n_value),
                "prompt": self._t("demo_round_2_prompt", n_value=n_value),
                "summary": self._t("demo_round_2_summary", n_value=n_value),
                "sequence": round_two + [nonmatch_two],
            },
            {
                "intro": self._t("demo_round_3_intro", n_value=n_value),
                "prompt": self._t("demo_round_3_prompt"),
                "summary": self._t("demo_round_3_summary"),
                "sequence": round_three + [round_three[0], nonmatch_three],
            },
            {
                "intro": self._t("demo_round_4_intro"),
                "prompt": self._t("demo_round_4_prompt", n_value=n_value),
                "summary": self._t("demo_round_4_summary"),
                "sequence": round_four + [round_four[0], round_four[1 % len(round_four)]],
            },
        ]

    def _demo_sliding_rule_text(self, n_value: int) -> str:
        alphabet = [chr(index) for index in range(ord("S"), ord("Z") + 1)] + [chr(index) for index in range(ord("A"), ord("R") + 1)]
        base_letters = [alphabet[index % len(alphabet)] for index in range(max(n_value, 1))]
        sequence = "-".join(base_letters + [base_letters[0]])
        next_reference = base_letters[1] if len(base_letters) > 1 else base_letters[0]
        return self._t(
            "demo_sliding_rule",
            n_value=n_value,
            sequence=sequence,
            next_reference=next_reference,
        )

    def _demo_feedback_key(self) -> str:
        expected_indices = {
            index
            for index in range(len(self.sequence))
            if self.n is not None and index >= self.n and self.sequence[index] == self.sequence[index - self.n]
        }
        pressed_indices = {
            index
            for index, result in enumerate(self.results)
            if result.is_key_pressed == "Yes"
        }
        missed = expected_indices - pressed_indices
        extra = pressed_indices - expected_indices
        if not missed and not extra:
            return "demo_feedback_perfect"
        if missed and extra:
            return "demo_feedback_mixed"
        if missed:
            return "demo_feedback_missed"
        return "demo_feedback_extra"

    def generate_sequence(self, num_trials: int) -> list[str]:
        if self.n is None:
            return []

        sequence: list[str] = []
        max_letter_usage = 4
        letters = [chr(index) for index in range(65, 91)]
        letter_counts = {letter: 0 for letter in letters}
        num_matches_desired = int((num_trials - self.n) * (self.rules.match_probability_percent / 100))
        total_matches = 0

        for index in range(num_trials):
            if index < self.n:
                available_letters = [letter for letter in letters if letter_counts[letter] < max_letter_usage]
                letter = random.choice(available_letters)
            else:
                should_match = total_matches < num_matches_desired and random.random() < (
                    num_matches_desired - total_matches
                ) / max(num_trials - index, 1)
                if should_match:
                    letter = sequence[index - self.n]
                    total_matches += 1
                else:
                    available_letters = [
                        letter
                        for letter in letters
                        if letter_counts[letter] < max_letter_usage and letter != sequence[index - self.n]
                    ]
                    letter = random.choice(available_letters) if available_letters else random.choice(letters)
            sequence.append(letter)
            letter_counts[letter] += 1
        return sequence

    def show_next_letter(self) -> None:
        if not self.is_playing or len(self.results) >= len(self.sequence):
            if self.state == "playing":
                self._complete_actual_block()
            elif self.state == "demo_playing":
                self._complete_demo_round()
            return

        self.current_letter = self.sequence[len(self.results)]
        letter_start_time = time.time()
        self.results.append(
            TrialResult(
                letter=self.current_letter,
                match_or_not_match="",
                timestamp_letter_appeared=letter_start_time,
                timestamp_letter_disappeared=None,
                is_key_pressed="No",
            )
        )
        self.status_label.config(text=self.current_letter, font=("Arial", 120, "bold"))
        self.detail_label.config(text=self.demo_round_prompt if self.state == "demo_playing" else "")
        display_time_ms = self.demo_display_time_ms if self.state == "demo_playing" else self.rules.display_time_ms
        self.letter_hide_after_id = self.root.after(display_time_ms, self.hide_letter)

    def hide_letter(self) -> None:
        self.letter_hide_after_id = None
        if self.n is None or not self.results:
            return
        current = self.results[-1]
        current.match_or_not_match = "MATCH" if self.is_match() else "NOT_MATCH"
        current.timestamp_letter_disappeared = time.time()
        self.status_label.config(text="", font=("Arial", 36, "bold"))
        self.detail_label.config(text=self.demo_round_prompt if self.state == "demo_playing" else "")
        intertrial_interval_ms = (
            self.demo_intertrial_interval_ms if self.state == "demo_playing" else self.rules.intertrial_interval_ms
        )
        self.next_letter_after_id = self.root.after(intertrial_interval_ms, self.show_next_letter)

    def check_match(self) -> None:
        if not self.is_playing or not self.current_letter or not self.results:
            return
        current = self.results[-1]
        if current.is_key_pressed == "Yes":
            return
        is_match = self.is_match()
        self.status_label.config(text=self.current_letter or "", font=("Arial", 120, "bold"))
        self.detail_label.config(text=self.demo_round_prompt if self.state == "demo_playing" else "")
        self.root.configure(bg="#052E16" if is_match else "#7F1D1D")
        current.is_key_pressed = "Yes"
        self.reset_color_after_id = self.root.after(400, lambda: self.root.configure(bg="#111827"))

    def is_match(self) -> bool:
        if self.n is None or len(self.results) <= self.n:
            return False
        previous_letter_index = len(self.results) - self.n - 1
        return self.current_letter == self.sequence[previous_letter_index]

    def _complete_actual_block(self) -> None:
        if self.n is None:
            return
        self._cancel_after("letter_hide_after_id")
        self._cancel_after("next_letter_after_id")
        self.is_playing = False
        block_results = list(self.results)
        self.completed_blocks.append((self.current_block, self.n, block_results))
        self._play_stage_end_signal()
        self.game_stage_completed = True
        self.state = "game_stage_complete"
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("block_ended"), font=("Arial", 34, "bold"))
        self.detail_label.config(text=self._t("preparing_next"))
        self.stage_transition_after_id = self.root.after(1000, self._advance_to_next_stage)

    def finish_session(self) -> None:
        self._clear_runtime_callbacks()
        self.state = "game_end"
        self.is_playing = False
        self.session_started = False
        self._emit_command("STOP_RECORDING")
        score = self.calculate_score()
        self.session_export_path = self.export_session_results()
        if self.session is not None:
            append_master_control_row(
                self.master_control_path,
                [
                    self.session.participant_name,
                    self.session.participant_id,
                    self.session.age,
                    str(self.session.n_value),
                    "✓" if self.session.relax_audio_enabled else "",
                    f"{score:.2f}",
                    self.session.note,
                    "✓" if self.consent_accepted_var.get() else "",
                ],
            )
        self._stop_relax_audio()
        self._set_message_layout(compact=True)
        self.status_label.config(text=self._t("block_ended"), font=("Arial", 34, "bold"))
        if self.session_export_path is not None:
            self.detail_label.config(
                text=self._t("experiment_finished_saved", score=score, filename=self.session_export_path.name)
            )
        else:
            self.detail_label.config(text=self._t("experiment_finished", score=score))
        self._hide_primary_action()
        self._hide_secondary_action()
        self.session_ready = False

    def calculate_score(self) -> float:
        trials = [trial for _, _, block_results in self.completed_blocks for trial in block_results]
        if not trials:
            return 0.0
        correct = 0
        for trial in trials:
            if trial.match_or_not_match == "MATCH" and trial.is_key_pressed == "Yes":
                correct += 1
            elif trial.match_or_not_match == "NOT_MATCH" and trial.is_key_pressed == "No":
                correct += 1
        return round((correct / len(trials)) * 100.0, 2)

    def export_session_results(self) -> Path | None:
        if self.session is None or not self.completed_blocks:
            return None

        result_folder = self.assets_dir / "result"
        result_folder.mkdir(exist_ok=True)
        date_token = datetime.now().strftime("%Y-%m-%d")
        arrangement_token = self._session_arrangement_token()
        file_token = self._safe_token(self.session.participant_id)
        output_file = result_folder / f"{file_token}_{date_token}_{arrangement_token}.csv"
        with output_file.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "participantName",
                    "participantId",
                    "age",
                    "dateExperimentStart",
                    "timeExperimentStart",
                    "blockNumber",
                    "nValue",
                    "trialNumber",
                    "letter",
                    "matchOrNotMatch",
                    "timestampLetterAppeared",
                    "timestampLetterDisappeared",
                    "isKeyPressed",
                    "note",
                    "sessionArrangement",
                ],
            )
            writer.writeheader()
            for block_number, n_value, results in self.completed_blocks:
                for trial_index, result in enumerate(results, start=1):
                    writer.writerow(
                        {
                            "participantName": self.session.participant_name,
                            "participantId": self.session.participant_id,
                            "age": self.session.age,
                            "dateExperimentStart": self.date_experiment or "",
                            "timeExperimentStart": self.experiment_start_time or "",
                            "blockNumber": block_number,
                            "nValue": n_value,
                            "trialNumber": trial_index,
                            "letter": result.letter,
                            "matchOrNotMatch": result.match_or_not_match,
                            "timestampLetterAppeared": result.timestamp_letter_appeared,
                            "timestampLetterDisappeared": result.timestamp_letter_disappeared,
                            "isKeyPressed": result.is_key_pressed,
                            "note": self.session.note,
                            "sessionArrangement": arrangement_token,
                        }
                    )
        return output_file

    def _calculate_game_trials(self, duration_minutes: float) -> int:
        return calculate_trial_count(
            max(duration_minutes, 0.1),
            self.rules.display_time_ms,
            self.rules.intertrial_interval_ms,
        )

    def _session_arrangement_token(self) -> str:
        if self.session is None:
            return "ABC"
        mapping = {"relax": "A", "game": "B", "break": "C"}
        ordered_stages = sorted(self.session.session_stages, key=lambda stage: stage.order)
        return "".join(mapping.get(stage.kind, "X") for stage in ordered_stages)

    def _entry_value(self, key: str) -> str:
        widget = self.examiner_fields[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end").strip()
        return widget.get().strip()

    @staticmethod
    def _safe_token(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
        return cleaned or "participant"

    @staticmethod
    def _coerce_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @staticmethod
    def _coerce_positive_int(value: object, *, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _emit_command(command: str) -> None:
        print(f"EEG_CMD:{command}", flush=True)

    @staticmethod
    def _resolve_language(value: str) -> str:
        normalized = (value or "en").strip().lower()
        return normalized if normalized in TRANSLATIONS else "en"

    def _t(self, key: str, **kwargs) -> str:
        template = TRANSLATIONS[self.language_code].get(key, TRANSLATIONS["en"].get(key, key))
        return template.format(**kwargs)

    def _stage_name(self, kind: str) -> str:
        return {
            "relax": self._t("relax"),
            "break": self._t("break"),
            "game": self._t("game"),
        }.get(kind, kind.title())

    @staticmethod
    def _stage_key(label: str) -> str:
        normalized = label.strip().lower()
        if normalized in {"relax", "entspannung", "thu gian", "thư giãn"}:
            return "relax"
        if normalized in {"break", "pause", "nghi", "nghỉ"}:
            return "break"
        return "game"

    def _cancel_after(self, attr_name: str) -> None:
        callback_id = getattr(self, attr_name)
        if callback_id is None:
            return
        try:
            self.root.after_cancel(callback_id)
        except Exception:
            pass
        setattr(self, attr_name, None)

    def _clear_runtime_callbacks(self) -> None:
        for attr_name in (
            "countdown_after_id",
            "stage_transition_after_id",
            "letter_hide_after_id",
            "next_letter_after_id",
            "reset_color_after_id",
            "second_beep_after_id",
        ):
            self._cancel_after(attr_name)

    def _start_relax_audio(self) -> None:
        if not self.relax_audio_path.exists():
            return
        self._stop_relax_audio()
        self.relax_audio_stop_event = threading.Event()

        def loop_audio() -> None:
            while not self.relax_audio_stop_event.is_set():
                try:
                    process = subprocess.Popen(["afplay", str(self.relax_audio_path)])
                except Exception:
                    self.relax_audio_process = None
                    return
                self.relax_audio_process = process
                while process.poll() is None:
                    if self.relax_audio_stop_event.wait(0.2):
                        try:
                            process.terminate()
                        except Exception:
                            pass
                        break
                self.relax_audio_process = None

        self.relax_audio_thread = threading.Thread(target=loop_audio, daemon=True)
        self.relax_audio_thread.start()

    def _stop_relax_audio(self) -> None:
        self.relax_audio_stop_event.set()
        process = self.relax_audio_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass
        self.relax_audio_process = None

    def _on_root_close(self) -> None:
        self._stop_relax_audio()
        self.root.destroy()

    def _play_stage_end_signal(self) -> None:
        self.root.bell()
        if self.examiner_window is not None:
            self.examiner_window.bell()
        self._cancel_after("second_beep_after_id")

        def second_beep() -> None:
            self.second_beep_after_id = None
            self.root.bell()
            if self.examiner_window is not None:
                self.examiner_window.bell()

        self.second_beep_after_id = self.root.after(180, second_beep)


def run_game() -> None:
    assets_dir = Path(__file__).resolve().parent
    try:
        root = tk.Tk()
        NBackGameController(root, assets_dir)
        root.mainloop()
    except Exception as exc:
        try:
            language_code = NBackGameController._resolve_language(os.environ.get("EEG_GAME_LANGUAGE", "en"))
            messagebox.showerror(
                TRANSLATIONS[language_code]["launch_failed_title"],
                TRANSLATIONS[language_code]["launch_failed_message"].format(error=exc),
            )
        except Exception:
            pass
        sys.exit(1)
