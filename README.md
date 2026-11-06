# 04 — Agendador de tarefas com Python

Projeto complementar às aulas de agendamento. Ele executa o ETL do projeto 03 ou faz um **backup consistente** de um banco SQLite, uma única vez ou por horário. Não usa comandos livres e não exige bibliotecas extras.

## Executar no Windows

Use o terminal nesta pasta:

```powershell
# Executar ETL do projeto 03 agora
python agendador.py --tarefa etl --uma-vez

# Criar backup do banco atualizado
python agendador.py --tarefa backup --uma-vez

# Reexecutar ETL a cada 30 minutos
python agendador.py --tarefa etl --intervalo 30

# Criar backup todos os dias às 10h no horário do computador
python agendador.py --tarefa backup --hora 10:00
```

A tarefa `backup` precisa que o banco tenha sido criado pela tarefa `etl` antes. Os backups ficam em `backups/` e o histórico em `logs/agendador.log`.

**Importante:** para executar em horários programados, o script precisa continuar aberto. No Windows, se quiser agendamento mesmo sem terminal aberto, use o **Agendador de Tarefas do Windows** para chamar `python.exe` com `agendador.py --tarefa etl --uma-vez`. Não agende duas instâncias simultâneas para o mesmo banco.

## Testes

```powershell
python -m unittest discover -s tests -v
```

São usados dados locais de demonstração. Para dados reais, configure a origem e o banco com `--origem` e `--db`.
