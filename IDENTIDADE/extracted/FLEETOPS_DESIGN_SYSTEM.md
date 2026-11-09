# FleetOps — Design System

**Marca:** FleetOps — Gestão de Frotas Inteligente
**Slogan:** "Sua frota, sempre no controle." · Secundário: "Mais eficiência. Menos custos."
**Conceito do símbolo:** movimento, eficiência e controle, em design moderno e minimalista (um "F" estilizado em faixas inclinadas azuis e brancas).
**Stack do sistema:** Django + Django Templates (server-rendered), PostgreSQL, Docker.

---

## 1. Logos

| Variação | Uso | Arquivo sugerido |
|---|---|---|
| Horizontal (símbolo + "FleetOps") | Topo da sidebar, header, login | `static/img/logo-horizontal.svg` |
| Vertical (símbolo acima do nome) | Telas de boas-vindas, splash | `static/img/logo-vertical.svg` |
| Ícone do app (símbolo em quadrado arredondado, borda azul) | App/PWA | `static/img/app-icon.png` |
| Favicon (símbolo, 32px e 16px) | Aba do navegador | `static/img/favicon.ico` |
| Variação sobre fundo claro | Documentos, PDFs, e-mails | `static/img/logo-light.svg` |
| Variação monocromática (cinza) | Marca d'água, rodapé | `static/img/logo-mono.svg` |

Estrutura do wordmark: "Fleet" em branco + "Ops" em azul `#2563EB`, peso Bold/Semibold. Subtítulo em caixa alta com espaçamento largo: "GESTÃO DE FROTAS INTELIGENTE".

> Os arquivos de logo precisam ser exportados/recortados da imagem original (ou do arquivo de design de origem) e salvos nos caminhos acima.

## 2. Paleta de cores

| Token | Nome | HEX | Uso |
|---|---|---|---|
| `--fo-primary` | Azul Principal | `#2563EB` | Botões primários, links, itens ativos, destaques |
| `--fo-primary-dark` | Azul Escuro | `#1E40AF` | Hover do primário, gradientes |
| `--fo-bg` | Fundo | `#0B1424` | Fundo da aplicação |
| `--fo-surface` | Superfície | `#1F2937` | Cards, inputs, tabelas, modais |
| `--fo-text` | Texto | `#E5E7EB` | Texto principal |
| `--fo-success` | Sucesso | `#22C55E` | Ativo, Em Operação, indicadores positivos |
| `--fo-warning` | Atenção | `#F59E0B` | Manutenção, documentos a vencer |
| `--fo-danger` | Erro | `#EF4444` | Erros, indisponível, documentos vencidos |

Complementares (derivados): `--fo-text-muted #9CA3AF`, `--fo-inactive #6B7280`, sidebar `#0E1A2E`, bordas `rgba(229,231,235,.12)`.

## 3. Tipografia

- **Família:** Montserrat (Google Fonts)
- **Pesos:** Light 300 · Regular 400 · Medium 500 · Semibold 600 · Bold 700
- **Hierarquia sugerida:** H1 28–32px Bold · H2 22px Bold · H3 18px Semibold · corpo 14–16px Regular · rótulos 12–13px Medium · KPIs 28px Bold

## 4. Ícones

Estilo outline, traço fino, cor azul principal. Usar **Lucide** (equivalentes):

| Função | Ícone Lucide |
|---|---|
| Início/Dashboard | `home` / `layout-dashboard` |
| Desempenho/Velocímetro | `gauge` |
| Localização | `map-pin` |
| Veículo | `car` |
| Caminhão/Frota | `truck` |
| Documentos/Relatórios | `file-text` |
| Agenda/Agendamento | `calendar-days` |
| Manutenção | `wrench` |
| Estatísticas | `bar-chart-3` |
| Notificações | `bell` |
| Configurações | `settings` |
| Usuário/Perfil | `user` |
| Buscar | `search` |
| Filtrar | `filter` |
| Download | `download` |
| Upload | `upload` |
| Sincronizar/Atualizar | `refresh-cw` |
| Alerta | `alert-triangle` |
| Combustível/Abastecimento | `fuel` |
| Rota/Percurso | `route` |

## 5. Componentes de UI

- **Botão primário:** fundo `#2563EB`, texto branco, raio 8px, com ícone de seta opcional. Hover `#1E40AF`.
- **Botão secundário:** transparente, borda sutil, texto claro.
- **Link:** azul, com seta →.
- **Badges de status (pílula com ponto colorido):** Ativo (verde), Atenção (laranja), Erro (vermelho), Inativo (cinza).
- **Campo de pesquisa:** input com ícone de lupa, fundo superfície, placeholder "Pesquisar...".
- **Select:** fundo superfície com seta ao lado direito.
- **Toggle:** ligado = azul, desligado = superfície.
- **Barra de progresso:** trilho superfície, preenchimento azul, percentual à direita.
- **Foco:** anel azul translúcido (`box-shadow: 0 0 0 3px rgba(37,99,235,.35)`).

Implementação pronta em `static/css/fleetops.css` (classes `.fo-btn`, `.fo-badge`, `.fo-input`, `.fo-select`, `.fo-toggle`, `.fo-progress`, `.fo-card`, `.fo-kpi`, `.fo-table`, `.fo-nav`).

## 6. Layout / Preview da interface

**Estrutura:** sidebar fixa à esquerda (240px) + área principal com topbar.

**Sidebar:** logo horizontal no topo; menu: Dashboard · Frota · Manutenções · Abastecimento · Relatórios · Configurações; item ativo com fundo azul sólido e texto branco; rodapé com usuário ("Administrador") e menu de conta.

**Topbar:** título da página + subtítulo ("Visão geral da sua frota"), sino de notificações e avatar do usuário.

**Dashboard:**
1. Linha de 4 cards KPI (ícone + valor + rótulo + variação %):
   - Veículos Ativos — 128 (+2%)
   - Manutenções Pendentes — 12 (+12%)
   - Combustível/Mês — 8.4k L (+12%)
   - Total Percorrido — 24.6k km (+5%)
2. Abaixo: gráfico de linha "Performance da Frota" (filtro "Últimos 6 meses", linha azul com área suave, eixo 0–100) ocupando ~2/3 da largura.
3. Ao lado: gráfico de rosca "Status da Frota" com percentual central (96%) e legenda: Em Operação (azul), Manutenção (laranja), Indisponível (vermelho).

*(Valores acima são de exemplo, vindos do mockup — substituir por dados reais do banco.)*

## 7. Aplicações

- **Ícone do app:** símbolo em quadrado arredondado com borda azul brilhante.
- **Tela de login:** card escuro centralizado, logo, texto "Faça login para continuar", campos, botão azul largo "Entrar".
- **Splash/boas-vindas:** logo vertical + "Gestão da frota inteligente".

## 8. Diretrizes de uso

- Mantenha o contraste adequado
- Use as cores da paleta oficial
- Não distorça o logo
- Respeite as áreas de proteção
- Mantenha a consistência visual

## 9. Elementos decorativos

Faixas diagonais azuis nos cantos (superior esquerdo e inferior direito) como assinatura visual em telas de destaque (login, splash, banners). Gradientes sutis de `#2563EB` → `#1E40AF`. Imagens de veículos escuros com iluminação azul como hero opcional.
