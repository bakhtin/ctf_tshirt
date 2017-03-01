# ctf_tshirt
Task for the attack-defense CTF training at Innopolis University

## Bugs
- Suffers from early client disconnect (by hitting Ctrl+C). Socket doesn't have enough time to close itself, thus enters infinite loop. Still not fixed in Python 3.6 :(
