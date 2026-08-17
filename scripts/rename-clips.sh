#!/usr/bin/env bash
#
# rename-clips.sh — swap one piece of text inside .mp4 filenames.
#
# Written for the bash macOS actually ships (3.2.57), so: no arrays, no
# `set -u`, no associative anything. It has to survive filenames with spaces
# and `#` in them, because the Desktop this runs on is full of them.
#
# Nothing is renamed until the complete list has been printed and confirmed.

set -e
set -o pipefail

usage() {
    cat <<'EOF'
rename-clips.sh — เปลี่ยนข้อความในชื่อไฟล์ .mp4

  bash scripts/rename-clips.sh
      ถามค่าทั้งสอง ทำงานบน ~/Desktop

  bash scripts/rename-clips.sh hf Project1
      hf_20260815_214524_2333c9c8.mp4  →  Project1_20260815_214524_2333c9c8.mp4

  bash scripts/rename-clips.sh hf Project1 ~/Movies
      โฟลเดอร์อื่น

  bash scripts/rename-clips.sh ~/Movies
      ใส่แค่โฟลเดอร์ แล้วให้มันถามค่าทั้งสอง

ตัวเลือก
  -a, --all    เปลี่ยนทุกจุดที่เจอในชื่อ (ปกติเปลี่ยนแค่จุดแรก)
  -r           ค้นในโฟลเดอร์ย่อยด้วย
  -h, --help   หน้านี้

แตะเฉพาะไฟล์ .mp4 / .MP4 และเฉพาะไฟล์ที่ชื่อมีข้อความนั้นจริง
ยังไม่เปลี่ยนอะไรจนกว่าจะเห็นรายการครบแล้วตอบ y
EOF
}

ALL=0
RECURSE=0
FROM=""
TO=""
TO_SET=0
DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        -a|--all)  ALL=1 ;;
        -r)        RECURSE=1 ;;
        -h|--help) usage; exit 0 ;;
        -*)        printf 'ไม่รู้จักตัวเลือก %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
        *)
            # A lone argument that is an existing directory means "work in
            # here, ask me for the text" -- otherwise `rename-clips.sh ~/Movies`
            # silently takes the path as the text to search for and reports
            # zero matches, which reads like the folder is empty.
            if   [ -z "$FROM" ] && [ -z "$DIR" ] && [ $# -eq 1 ] && [ -d "$1" ]; then DIR="$1"
            elif [ -z "$FROM" ];    then FROM="$1"
            elif [ "$TO_SET" = 0 ]; then TO="$1"; TO_SET=1
            elif [ -z "$DIR" ];     then DIR="$1"
            else printf 'มี argument เกินมา: %s\n' "$1" >&2; exit 2
            fi
            ;;
    esac
    shift
done

[ -n "$FROM" ] || read -r -p 'เปลี่ยนจาก : ' FROM
if [ "$TO_SET" = 0 ]; then
    read -r -p 'เป็น       : ' TO
    TO_SET=1
fi
[ -n "$DIR" ] || DIR="$HOME/Desktop"

if [ -z "$FROM" ]; then
    echo 'ต้องบอกข้อความที่จะเปลี่ยน' >&2
    exit 2
fi

# FROM is used as a bash pattern in ${name/FROM/TO}, so a glob character in it
# would match something other than itself. Refuse rather than quietly rename
# the wrong files -- bash has no literal-replace expansion to fall back on.
case "$FROM" in
    *'*'*|*'?'*|*'['*)
        echo 'ห้ามใช้ * ? [ ในข้อความที่จะเปลี่ยน — bash จะตีความเป็น pattern' >&2
        exit 2
        ;;
esac

if [ "$FROM" = "$TO" ]; then
    echo 'ข้อความเดิมกับข้อความใหม่เหมือนกัน ไม่มีอะไรต้องทำ'
    exit 0
fi

if [ ! -d "$DIR" ]; then
    printf 'ไม่มีโฟลเดอร์: %s\n' "$DIR" >&2
    exit 1
fi

TMP=$(mktemp -t renameclips)
trap 'rm -f "$TMP" "$TMP.tgt"' EXIT
: > "$TMP"
: > "$TMP.tgt"

if [ "$RECURSE" = 1 ]; then DEPTH=""; else DEPTH="-maxdepth 1"; fi

sub=""
[ "$RECURSE" = 1 ] && sub="  (รวมโฟลเดอร์ย่อย)"
blank=""
[ -z "$TO" ] && blank="   ← ปลายทางว่าง = ลบข้อความนั้นทิ้ง"
scope="เปลี่ยนแค่จุดแรก"
[ "$ALL" = 1 ] && scope="เปลี่ยนทุกจุดที่เจอ"

printf '\nโฟลเดอร์ : %s%s\n' "$DIR" "$sub"
printf 'เปลี่ยน  : "%s"  →  "%s"%s\n' "$FROM" "$TO" "$blank"
printf 'ขอบเขต   : เฉพาะ .mp4 · %s\n\n' "$scope"

n=0
multi=0
while IFS= read -r -d '' path; do
    name=$(basename "$path")

    # Only ever touch the stem. The extension is off limits -- searching for
    # "p" and replacing with "q" turned p_one.mp4 into q_one.mq4 while this
    # worked on the whole name, which is a broken file, not a renamed one.
    stem="${name%.*}"
    ext="${name##*.}"

    # Literal containment test -- quoting FROM inside the pattern stops any
    # remaining metacharacter from being interpreted.
    case "$stem" in
        *"$FROM"*) ;;
        *) continue ;;
    esac

    if [ "$ALL" = 1 ]; then
        newstem="${stem//$FROM/$TO}"
    else
        newstem="${stem/$FROM/$TO}"
    fi
    new="$newstem.$ext"
    [ "$new" = "$name" ] && continue

    printf '%s\0%s\0' "$path" "$new" >> "$TMP"
    printf '%s\n' "$new" >> "$TMP.tgt"
    n=$((n + 1))
    printf '  %s\n   → %s\n' "$name" "$new"

    # If replacing once and replacing everywhere disagree, the text appears
    # more than once in this name. Worth saying out loud: the default only
    # touches the first, which is right for a prefix and wrong if they meant
    # all of them.
    if [ "${stem/$FROM/$TO}" != "${stem//$FROM/$TO}" ]; then
        multi=$((multi + 1))
        printf '     ← ชื่อนี้มี "%s" มากกว่า 1 ที่\n' "$FROM"
    fi
done < <(find "$DIR" $DEPTH -type f -iname '*.mp4' -print0)

if [ "$n" = 0 ]; then
    printf 'ไม่เจอไฟล์ .mp4 ที่ชื่อมี "%s" เลย ไม่มีอะไรถูกแตะ\n' "$FROM"
    exit 0
fi

dupes=$(sort "$TMP.tgt" | uniq -d || true)
if [ -n "$dupes" ]; then
    printf '\nหยุด — ชื่อปลายทางชนกัน ไฟล์พวกนี้จะกลายเป็นชื่อเดียวกัน:\n'
    printf '%s\n' "$dupes" | sed 's/^/  /'
    printf 'แก้ข้อความก่อนแล้วรันใหม่ ยังไม่มีไฟล์ไหนถูกเปลี่ยน\n'
    exit 1
fi

printf '\nรวม %d ไฟล์' "$n"
[ "$multi" -gt 0 ] && printf ' (%d ไฟล์มีข้อความซ้ำ — ดู ← ด้านบน ถ้าอยากเปลี่ยนทุกจุดใช้ -a)' "$multi"
printf '\n'

read -r -p 'ทำเลยไหม? (y/N) ' ans
case "$ans" in
    y|Y|yes|YES|Yes) ;;
    *) echo 'ยกเลิก ไม่มีไฟล์ไหนถูกแตะ'; exit 0 ;;
esac

ok=0
skipped=0
while IFS= read -r -d '' src && IFS= read -r -d '' dst; do
    d=$(dirname "$src")
    if [ -e "$d/$dst" ]; then
        printf '  ข้าม — มีไฟล์ชื่อนี้อยู่แล้ว: %s\n' "$dst"
        skipped=$((skipped + 1))
        continue
    fi
    mv -n -- "$src" "$d/$dst"
    ok=$((ok + 1))
done < "$TMP"

printf '\nเปลี่ยนแล้ว %d ไฟล์' "$ok"
[ "$skipped" -gt 0 ] && printf ' · ข้าม %d (ชื่อซ้ำของเดิม)' "$skipped"
printf '\n'
