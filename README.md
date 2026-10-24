# Revista presei

În fiecare dimineață, la puțin după 08:00 (ora României), scriptul verifică site-urile din `config/sites.txt`,
păstrează articolele care conțin cuvintele din `config/keywords.txt` și nu au mai fost trimise, apoi trimite
pe e-mail o pagină HTML cu ele. Istoricul rapoartelor este în căsuța de e-mail.

Workflow-ul nu face commit-uri în repository. Lista articolelor deja trimise (`data/seen.json`) se păstrează
între rulări în cache-ul GitHub Actions. La rulările locale, rapoartele se salvează în `reports/`
(`stiri_AAAA-LL-ZZ.html`), iar `data/` și `reports/` sunt excluse din git.

## Liste

- `config/sites.txt`: un site pe rând (pagina principală sau direct adresa RSS).
- `config/keywords.txt`: un subiect pe rând, cu variante despărțite prin ` | ` (de obicei engleză, apoi română).
  Cuvintele se compară după rădăcină, deci *plăți* găsește și *plata*, *plățile*. Regulile complete
  (ordinea cuvintelor, `*`, ghilimele, acronime) sunt explicate chiar la începutul fișierului.

## Rulare locală

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m stiri --dry-run     # doar generează în reports/ pagina cu tot ce ar primi un destinatar nou, fără e-mail
```

Pentru trimiterea e-mailului de pe calculator, setează aceleași variabile ca mai jos și rulează `python -m stiri`.

## Instalare pe GitHub (rulare automată zilnică)

1. Creează un **repository privat** pe GitHub și urcă proiectul în el.
2. Contul care trimite e-mailurile (recomandat: un Gmail dedicat):
   activează verificarea în doi pași (Cont Google → Securitate → Verificare în doi pași), apoi creează o
   **parolă de aplicație** la adresa <https://myaccount.google.com/apppasswords>. Opțiunea nu mai apare în
   meniul de Securitate, se ajunge la ea doar prin acest link. Copiază parola imediat: Google n-o mai afișează a doua oară.
3. În repository: **Settings → Secrets and variables → Actions → New repository secret**:

   | Secret          | Valoare                                            |
   |-----------------|----------------------------------------------------|
   | `SMTP_HOST`     | `smtp.gmail.com`                                   |
   | `SMTP_PORT`     | `465`                                              |
   | `SMTP_USER`     | adresa Gmail care trimite                          |
   | `SMTP_PASSWORD` | parola de aplicație (16 caractere)                 |
   | `MAIL_TO`       | destinatarul; mai mulți se despart prin virgulă (1)|

   (1) Fiecare adresă primește un e-mail separat, iar scriptul ține minte separat ce a trimis fiecăreia.
   O adresă nouă primește la primul e-mail toate articolele găsite în acel moment.

4. **Actions → Revista presei → Run workflow**, pentru un prim test. De acum rulează singur zilnic.

Dacă o rulare eșuează (de exemplu, parola nu mai e validă), GitHub trimite un e-mail proprietarului repository-ului.
