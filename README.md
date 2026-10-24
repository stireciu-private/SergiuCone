# Revista presei

În fiecare dimineață, la puțin după 08:00 (ora României), scriptul verifică site-urile din `config/sites.txt`,
păstrează articolele care conțin cuvintele din `config/keywords.txt` și nu au mai fost trimise, apoi trimite
pe e-mail o pagină HTML cu ele. Fiecare raport rămâne și în folderul `reports/` (`stiri_AAAA-LL-ZZ.html`).

## Liste

- `config/sites.txt`: un site pe rând (pagina principală sau direct adresa RSS).
- `config/keywords.txt`: un cuvânt sau o expresie pe rând. Majusculele și diacriticele nu contează.
  Un `*` la final prinde orice terminație: `dobânz*` găsește *dobânzi*, *dobânzile*, *dobânzilor*.

## Rulare locală

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m stiri --dry-run     # doar generează pagina în reports/, fără e-mail
```

Pentru trimiterea e-mailului de pe calculator, setează aceleași variabile ca mai jos și rulează `python -m stiri`.

## Instalare pe GitHub (rulare automată zilnică)

1. Creează un **repository privat** pe GitHub și urcă proiectul în el.
2. Contul care trimite e-mailurile (recomandat: un Gmail dedicat):
   activează verificarea în doi pași, apoi creează o **parolă de aplicație** (Cont Google → Securitate → Parole pentru aplicații).
3. În repository: **Settings → Secrets and variables → Actions → New repository secret**:

   | Secret          | Valoare                                            |
   |-----------------|----------------------------------------------------|
   | `SMTP_HOST`     | `smtp.gmail.com`                                   |
   | `SMTP_PORT`     | `465`                                              |
   | `SMTP_USER`     | adresa Gmail care trimite                          |
   | `SMTP_PASSWORD` | parola de aplicație (16 caractere)                 |
   | `MAIL_TO`       | destinatarul; mai mulți se despart prin virgulă    |

4. **Actions → Revista presei → Run workflow**, pentru un prim test. De acum rulează singur zilnic.

Dacă o rulare eșuează (de exemplu, parola nu mai e validă), GitHub trimite un e-mail proprietarului repository-ului.
