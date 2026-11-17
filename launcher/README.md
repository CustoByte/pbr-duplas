# PBR Duplas — Launcher

Launcher desktop para o mod de campanha cooperativa de Pokémon Battle Revolution.

## O que faz

- Inicia o jogo no Dolphin com um clique
- Verifica e baixa atualizações do GitHub Releases
- Interface com tema Bloodborne (escuro, dourado)

## Requisitos

- Windows 10/11 x64
- .NET 8 Desktop Runtime
- Dolphin Emulator
- Imagem do jogo (`.rvz` / `.iso`)

## Compilar

```bash
dotnet build -c Release
```

## Publicar executável único

```bash
dotnet publish src/PBRDuplasLauncher/PBRDuplasLauncher.csproj -c Release -r win-x64 --self-contained false -o publish
```

O executável fica em `publish/PBR Duplas.exe`.

## Configuração

Salva em `%LOCALAPPDATA%\PBRDuplas\config.json`:

- Caminho do jogo (RVZ/ISO)
- Caminho do Dolphin
- Repositório GitHub de atualizações
- Verificação automática ao abrir

## Estrutura

```
src/PBRDuplasLauncher/
  MainWindow.xaml        Interface (3 telas)
  Styles/                Tema Bloodborne
  Services/              Config, Update, GameLaunch
  Models/                Config e Release
```
