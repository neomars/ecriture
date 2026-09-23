#!/usr/bin/env python3
"""Builds the bundled English sample novel, Pride and Prejudice (Jane Austen,
1813, public domain), from the Project Gutenberg plain-text edition (#1342).

Usage:
    python3 scripts/build_pride_and_prejudice.py path/to/1342.txt

Writes ecriture-core/resources/default_projects/pride_and_prejudice.json.
The Project Gutenberg header, footer and trademark are stripped, as the
Project Gutenberg license requires when redistributing the text itself.
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ecriture-core/resources/default_projects/pride_and_prejudice.json"

SUMMARIES = [
    "Mrs. Bennet announces that Netherfield Park has been let to a rich young bachelor, Mr. Bingley, and urges her husband to call on him.",
    "Mr. Bennet has secretly visited Mr. Bingley and teases his family before revealing it.",
    "At the Meryton assembly, Bingley is charmed by Jane, while Darcy is judged proud after refusing to dance with Elizabeth, whom he finds merely \"tolerable\".",
    "Jane confesses her admiration for Bingley; the narrator contrasts Bingley's easy temper with Darcy's reserve.",
    "The Lucases and the Bennets discuss the ball; Charlotte Lucas excuses Darcy's pride.",
    "Charlotte advises Jane to show her feelings more openly; Darcy begins to admire Elizabeth's fine eyes, and she refuses to dance with him at Lucas Lodge.",
    "Jane rides to Netherfield in the rain and falls ill; Elizabeth walks three miles through the mud to nurse her.",
    "Bingley's sisters mock Elizabeth's muddy petticoats; a debate on what makes a truly accomplished woman.",
    "Mrs. Bennet visits Netherfield and embarrasses Elizabeth; Lydia extracts from Bingley the promise of a ball.",
    "Caroline Bingley flatters Darcy as he writes a letter; Elizabeth and Darcy spar about Bingley's impulsiveness.",
    "Elizabeth and Darcy discuss his faults: pride, and a resentment that, once lost, is lost forever.",
    "Jane and Elizabeth return home; Darcy resolves to show Elizabeth no further sign of admiration.",
    "A letter announces Mr. Collins, the cousin who will inherit Longbourn through the entail; he arrives.",
    "Mr. Collins praises his patroness, Lady Catherine de Bourgh, and reads Fordyce's Sermons until Lydia interrupts.",
    "Collins plans to marry one of the Bennet girls; in Meryton the sisters meet the charming Mr. Wickham, who exchanges a cold look with Darcy.",
    "Wickham tells Elizabeth that Darcy denied him the living promised by old Mr. Darcy.",
    "Jane refuses to think ill of either man; the Netherfield ball is announced.",
    "At the Netherfield ball, Elizabeth dances with Darcy and challenges him about Wickham, while her family's behaviour mortifies her.",
    "Mr. Collins proposes to Elizabeth, who firmly refuses him.",
    "Mrs. Bennet insists, but Mr. Bennet sides with Elizabeth: her mother will never see her again if she does not marry Collins, and he will never see her again if she does.",
    "The Bingley party leaves for London; Caroline's letter hints that Bingley will marry Georgiana Darcy.",
    "Charlotte Lucas accepts Mr. Collins for the security of an establishment, to Elizabeth's astonishment.",
    "The engagement is announced to the Bennets' dismay, and still no word comes from Bingley.",
    "Caroline confirms that Bingley will stay in London; Jane bears it quietly while Elizabeth blames Darcy and Bingley's sisters.",
    "The Gardiners spend Christmas at Longbourn; Mrs. Gardiner takes Jane to London and warns Elizabeth against Wickham.",
    "In London, Jane is coldly received by Caroline; Wickham turns his attentions to the heiress Miss King.",
    "Elizabeth travels through London to Hunsford with Sir William and Maria Lucas.",
    "Elizabeth arrives at Hunsford parsonage and admires how Charlotte manages Mr. Collins.",
    "Dinner at Rosings: Lady Catherine interrogates Elizabeth, who answers with unusual spirit.",
    "Darcy and his cousin Colonel Fitzwilliam arrive at Rosings and call at the parsonage.",
    "At Rosings, Elizabeth plays the pianoforte and teases Darcy about his reserve among strangers.",
    "Darcy calls on Elizabeth alone in an awkward visit; Charlotte suspects he is in love.",
    "Colonel Fitzwilliam reveals that Darcy saved a friend from an imprudent marriage: Elizabeth realises it was Bingley and Jane.",
    "Darcy's first proposal, full of pride and scorn for her family; Elizabeth refuses him, accusing him of ruining Jane's happiness and wronging Wickham.",
    "Darcy hands Elizabeth a letter explaining why he separated Bingley and Jane, and revealing Wickham's true history and his attempt to elope with Georgiana.",
    "Rereading the letter, Elizabeth recognises her own prejudice: \"Till this moment I never knew myself.\"",
    "Darcy and Fitzwilliam leave Rosings; Elizabeth reflects on the letter.",
    "Elizabeth and Maria leave Hunsford, Mr. Collins praising his happy situation.",
    "Lydia and Kitty meet their sisters at the inn: the regiment is going to Brighton, and Wickham is no longer courting Miss King.",
    "Elizabeth tells Jane about the proposal and Wickham's past; they decide not to expose him.",
    "The regiment leaves; Lydia is invited to Brighton, and Elizabeth warns her father in vain.",
    "Reflections on the Bennets' ill-matched marriage; the northern tour with the Gardiners is cut short to Derbyshire, near Pemberley.",
    "Touring Pemberley, Elizabeth hears the housekeeper's praise of Darcy; he appears unexpectedly and is remarkably civil to her and the Gardiners.",
    "Darcy introduces his sister Georgiana to Elizabeth; Bingley visits, and Elizabeth's feelings begin to change.",
    "Elizabeth visits Pemberley; Caroline's jibe about the militia backfires.",
    "Letters from Jane: Lydia has eloped with Wickham. Darcy finds Elizabeth in distress, and she hurries home.",
    "The journey home; Mr. Bennet searches London while the family despairs.",
    "Mr. Gardiner joins the search; Mr. Collins sends a cruel letter; Mr. Bennet returns home.",
    "Wickham and Lydia are found: he will marry her for a surprisingly modest settlement.",
    "Mr. Bennet regrets never having saved; Elizabeth realises Darcy would have suited her, just as it seems impossible.",
    "The shameless newlyweds visit Longbourn; Lydia lets slip that Darcy was at her wedding.",
    "Mrs. Gardiner reveals that Darcy found the couple and paid Wickham's debts; Elizabeth and Wickham talk.",
    "Wickham and Lydia leave for the north; Bingley returns to Netherfield and calls at Longbourn with Darcy.",
    "Dinner at Longbourn: Bingley's attention to Jane revives, while Darcy stays distant.",
    "Bingley proposes to Jane and is joyfully accepted.",
    "Lady Catherine descends on Longbourn to forbid Elizabeth to marry Darcy; Elizabeth refuses to promise anything.",
    "Mr. Collins writes to warn Mr. Bennet, who laughs at the very idea of Darcy and Elizabeth.",
    "Walking together, Elizabeth thanks Darcy for saving Lydia; he renews his proposal and she accepts.",
    "Jane can hardly believe it; Mr. Bennet consents once he learns what Darcy did for Lydia.",
    "Elizabeth and Darcy talk over how they fell in love; letters announce the engagement.",
    "Epilogue: the double marriage, the family's later fortunes, and life at Pemberley.",
]

CHARACTERS = [
    ("Elizabeth Bennet", "Protagonist", "Second of the five Bennet daughters: lively, witty and quick to judge. She must learn to see past her first impressions.",
     [("char_2", "Love interest", "She despises him after the Meryton ball, refuses his first proposal, then comes to love him."),
      ("char_3", "Sister", "Her closest confidante, whose gentle nature she both admires and protects."),
      ("char_5", "Deceived friend", "She believes Wickham's account of Darcy until Darcy's letter reveals the truth."),
      ("char_7", "Father", "His favourite daughter; they share the same ironic wit."),
      ("char_9", "Rejected suitor", "She refuses Mr. Collins's pompous proposal."),
      ("char_10", "Best friend", "Charlotte's marriage to Collins shocks her.")]),
    ("Fitzwilliam Darcy", "Love interest", "Master of Pemberley, rich, proud and reserved. Beneath his pride lies a generous and honourable man.",
     [("char_4", "Close friend", "He persuades Bingley that Jane does not love him."),
      ("char_5", "Enemy", "Wickham squandered his inheritance and tried to elope with Georgiana."),
      ("char_11", "Nephew", "Lady Catherine intends him to marry her daughter."),
      ("char_12", "Sister", "His younger sister, whom he protects fiercely.")]),
    ("Jane Bennet", "Supporting", "The eldest and most beautiful Bennet daughter, sweet-tempered and always ready to think well of others.",
     [("char_4", "Love interest", "They fall in love at once, are separated, then reunited."),
      ("char_1", "Sister", "She confides in Elizabeth but hides her own suffering.")]),
    ("Charles Bingley", "Supporting", "Darcy's amiable friend, who rents Netherfield Park. Good-natured but easily led.",
     [("char_3", "Love interest", "He loves Jane but lets Darcy and his sisters persuade him to leave.")]),
    ("George Wickham", "Antagonist", "A handsome militia officer, son of the late Mr. Darcy's steward: charming, idle and unscrupulous.",
     [("char_6", "Seducer", "He elopes with Lydia and has to be paid to marry her."),
      ("char_2", "Rival", "He slanders Darcy to everyone in Meryton.")]),
    ("Lydia Bennet", "Supporting", "The youngest Bennet daughter, fifteen, flirtatious and thoughtless.",
     [("char_5", "Husband", "She elopes with him from Brighton."),
      ("char_8", "Mother", "Her mother's favourite, whose indulgence she exploits.")]),
    ("Mr. Bennet", "Supporting", "The ironic, detached father of the family, who retreats to his library rather than govern his household.",
     [("char_8", "Wife", "An ill-matched marriage he treats with sarcasm.")]),
    ("Mrs. Bennet", "Supporting", "A nervous, foolish mother whose one aim in life is to see her daughters married.",
     [("char_9", "Hoped-for son-in-law", "She is furious when Elizabeth refuses him.")]),
    ("William Collins", "Comic relief", "A pompous, obsequious clergyman, heir to Longbourn through the entail.",
     [("char_11", "Patroness", "He worships Lady Catherine, who gave him his living."),
      ("char_10", "Wife", "She accepts him for a comfortable home.")]),
    ("Charlotte Lucas", "Supporting", "Elizabeth's sensible friend, twenty-seven, who marries for security rather than love.",
     []),
    ("Lady Catherine de Bourgh", "Antagonist", "Darcy's imperious aunt, mistress of Rosings Park.",
     [("char_1", "Opponent", "She comes to Longbourn to forbid Elizabeth to marry Darcy.")]),
    ("Georgiana Darcy", "Minor", "Darcy's shy sixteen-year-old sister, almost seduced by Wickham at Ramsgate.",
     [("char_1", "Friend", "She quickly grows fond of Elizabeth.")]),
]

NOTES = [
    ("Longbourn", "Place", "The Bennet family estate near the village of Meryton, in Hertfordshire. Entailed on Mr. Collins."),
    ("Netherfield Park", "Place", "The grand house near Longbourn rented by Mr. Bingley, scene of Jane's illness and of the ball."),
    ("Meryton", "Place", "The market town where the militia is quartered and where the Bennet sisters meet Wickham."),
    ("Hunsford & Rosings Park", "Place", "In Kent: Mr. Collins's parsonage, next to Lady Catherine's grand estate, where Darcy first proposes."),
    ("Pemberley", "Place", "Darcy's magnificent estate in Derbyshire. Seeing it, Elizabeth begins to change her mind about its master."),
    ("The entail", "Background", "Longbourn can only pass to a male heir: on Mr. Bennet's death it will go to Mr. Collins, leaving his daughters without a home."),
]

PLOTLINES = [("pl_1", "Elizabeth & Darcy"), ("pl_2", "Jane & Bingley"), ("pl_3", "Lydia & Wickham"), ("pl_4", "Collins & Charlotte")]

# (plotline, chapter, title, content)
CARDS = [
    ("pl_2", 3, "First sight", "At the Meryton assembly, Bingley dances twice with Jane."),
    ("pl_1", 3, "\"Tolerable\"", "Darcy refuses to dance with Elizabeth, who overhears his slight."),
    ("pl_1", 11, "Pride and prejudice", "Elizabeth and Darcy spar about his faults at Netherfield."),
    ("pl_3", 16, "Wickham's tale", "Wickham tells Elizabeth how Darcy cheated him of his living."),
    ("pl_4", 19, "Collins proposes", "Mr. Collins proposes to Elizabeth, who refuses him."),
    ("pl_2", 21, "Departure", "Bingley leaves Netherfield for London without a word to Jane."),
    ("pl_4", 22, "Charlotte accepts", "Charlotte Lucas accepts Collins for the security of a home."),
    ("pl_1", 34, "First proposal", "Darcy proposes at Hunsford; Elizabeth refuses him with scorn."),
    ("pl_1", 35, "The letter", "Darcy explains himself and reveals Wickham's true character."),
    ("pl_3", 41, "Brighton", "Lydia follows the regiment to Brighton."),
    ("pl_1", 43, "Pemberley", "Elizabeth visits Pemberley and meets a transformed Darcy."),
    ("pl_3", 46, "Elopement", "Lydia runs away with Wickham."),
    ("pl_3", 52, "Darcy's secret", "Darcy has found the couple and paid for the marriage."),
    ("pl_2", 55, "Engagement", "Bingley proposes to Jane and is accepted."),
    ("pl_1", 56, "Lady Catherine", "Lady Catherine tries to forbid the match; Elizabeth stands firm."),
    ("pl_1", 58, "Second proposal", "Darcy proposes again, and Elizabeth accepts."),
]

# (chapter, title, description, characters)
KEY_EVENTS = [
    (3, "The Meryton assembly", "Bingley admires Jane; Darcy slights Elizabeth.", ["char_1", "char_2", "char_3", "char_4"]),
    (34, "The first proposal", "Darcy proposes at Hunsford and is refused.", ["char_1", "char_2"]),
    (46, "Lydia's elopement", "Lydia runs away with Wickham, threatening the family's reputation.", ["char_5", "char_6"]),
    (55, "Jane and Bingley engaged", "Bingley returns and proposes to Jane.", ["char_3", "char_4"]),
    (58, "The second proposal", "Darcy proposes again and Elizabeth accepts.", ["char_1", "char_2"]),
]


def chapters(text):
    text = text.replace("\r\n", "\n")
    start = text.index("*** START OF THIS PROJECT GUTENBERG EBOOK")
    end = text.index("End of the Project Gutenberg EBook")
    body = text[start:end]
    parts = re.split(r"^Chapter (\d+)\n", body, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        number = int(parts[i])
        paragraphs = [" ".join(line.strip() for line in p.splitlines()).strip() for p in parts[i + 1].split("\n\n")]
        paragraphs = [re.sub(r"_([^_]+)_", r"<i>\1</i>", p) for p in paragraphs if p]
        out.append((number, "\n\n".join(paragraphs)))
    return out


def main(source):
    chaps = chapters(Path(source).read_text(encoding="ascii"))
    assert [n for n, _ in chaps] == list(range(1, 62)), "expected chapters 1..61"
    assert len(SUMMARIES) == 61
    manuscript = [{
        "id": f"chap_{n}", "type": "chapter", "title": f"Chapter {n}", "summary": SUMMARIES[n - 1],
        "children": [{"id": f"scene_{n}_1", "type": "scene", "title": "Scene 1", "content": content}],
    } for n, content in chaps]
    words = sum(len(re.sub(r"<[^>]+>", "", c).split()) for _, c in chaps)
    data = {
        "settings": {"title": "Pride and Prejudice", "daily_goal": 500, "overall_goal": 50000,
                     "overall_written": words, "daily_written": 0, "lang": "en"},
        "manuscript": manuscript,
        "plot": {
            "plotlines": [{"id": i, "title": t} for i, t in PLOTLINES],
            "cards": [{"id": f"card_{k}", "plotline_id": pl, "scene_id": f"scene_{ch}_1", "title": t, "content": c}
                      for k, (pl, ch, t, c) in enumerate(CARDS, 1)],
        },
        "characters": [{"id": f"char_{k}", "name": n, "role": r, "description": d,
                        "relations": [{"target_id": t, "type": ty, "description": de} for t, ty, de in rel]}
                       for k, (n, r, d, rel) in enumerate(CHARACTERS, 1)],
        "story_notes": [{"id": f"note_{k}", "title": t, "type": ty, "content": c} for k, (t, ty, c) in enumerate(NOTES, 1)],
        "key_events": [{"id": f"evt_{k}", "chapter_id": f"chap_{ch}", "title": t, "description": d, "characters": cs}
                       for k, (ch, t, d, cs) in enumerate(KEY_EVENTS, 1)],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(manuscript)} chapters, {words} words")


if __name__ == "__main__":
    main(sys.argv[1])
