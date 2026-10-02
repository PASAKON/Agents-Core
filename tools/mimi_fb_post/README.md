# Mimi page: schedule a photo post from the Page profile (winbox Chrome :9281)

Stop-gap until the Graph API token lands (GitHub issue PASAKON/Agents-Core#204). Skill: `BROWSER_OPERATOR_Protocol_Playbook` §Facebook photo post.

Setup: `export FBX_WORK=/some/dir`, put `run_fbx.sh` in it and `mkdir $FBX_WORK/fb`. The poster must already be on winbox in `C:\mooniex\khaoniao\sched\`.

    python3 tools/mimi_fb_post/schedule_photo_post.py <key> <poster.png> <caption.txt> <day-of-month> <วัน<weekday>>
    python3 tools/mimi_fb_post/fix_post_caption.py   <key> <poster.png> <caption.txt> <day-of-month> <วัน<weekday>>   # never presses schedule

`schedule_photo_post.py` gates (box length, AI chip ON, schedule string, date/time inputs), presses «กำหนดเวลา», reads the Scheduled list back and repairs a dropped caption through «แก้ไขโพสต์» (Facebook drops the caption of every composer-scheduled photo post, 4 of 4 on 2026-10-02). It never touches «ลบโพสต์». One browser job at a time.
