# 🎨 Plan de Implementación - ROC Skincare Styling

## 📋 Resumen Ejecutivo

**Objetivo**: Aplicar los estilos profesionales de ROC Skincare al sistema de gestión de recibos multi-trabajador, mejorando la experiencia de usuario y profesionalismo de la aplicación Streamlit.

**Basado en**: [Roc skincare style.txt](Roc%20skincare%20style.txt) - Análisis exhaustivo de https://www.rocskincare.com/

**Estado**: 📝 Planificado - Pendiente de ejecución

**Prioridad**: Media (mejora de UX/UI, no afecta funcionalidad)

**Timeline**: 11-16 días de desarrollo

---

## 🎯 Objetivos de la Implementación

### Objetivos Principales
1. **Identidad Visual Profesional**: Aplicar paleta de colores premium (azul marino + dorado)
2. **Consistencia UI**: Estandarizar componentes (botones, tarjetas, formularios)
3. **Experiencia Premium**: Mejorar percepción de calidad del sistema
4. **Responsive Design**: Asegurar visualización óptima en todos los dispositivos

### Objetivos Secundarios
1. Mejorar accesibilidad (WCAG AA)
2. Optimizar rendimiento visual
3. Mantener compatibilidad con Streamlit
4. Facilitar mantenimiento futuro

---

## 📐 Arquitectura de Implementación

### Estructura de Archivos Propuesta

```
gguf/
├── assets/                       # NUEVO - Assets estáticos
│   ├── css/
│   │   ├── roc_variables.css     # Variables CSS (colores, tipografía, espaciado)
│   │   ├── roc_components.css    # Componentes reutilizables
│   │   ├── roc_layout.css        # Layouts y grid systems
│   │   └── roc_theme.css         # Tema principal integrado
│   ├── images/
│   │   └── logo/                 # Logo personalizado (si aplica)
│   └── fonts/                    # Fuentes personalizadas (si es necesario)
├── modules/
│   └── ui/
│       ├── __init__.py
│       ├── components.py         # NUEVO - Componentes reutilizables
│       ├── styles.py             # NUEVO - Helper para inyección de estilos
│       └── themes.py             # NUEVO - Configuración de temas
└── doc/
    ├── Roc skincare style.txt    # Guía de estilos fuente
    └── ROC_COMPONENTS_LIBRARY.md # NUEVO - Documentación de componentes
```

---

## 🎨 Fase 1: Sistema de Diseño Base (2-3 días)

### 1.1 Variables CSS Globales

**Archivo**: `assets/css/roc_variables.css`

```css
:root {
  /* Colores Primarios */
  --roc-primary: #001E2B;
  --roc-primary-dark: #00161F;
  --roc-gold: #C6A052;
  --roc-gold-light: #D4B77A;
  --roc-white: #FFFFFF;
  
  /* Colores Secundarios */
  --roc-gray-light: #F5F5F5;
  --roc-gray-medium: #E8E8E8;
  --roc-gray: #6B6B6B;
  --roc-gray-dark: #404040;
  --roc-blue-gray: #8CA3B8;
  --roc-blue-light: #E6EEF4;
  
  /* Tipografía */
  --roc-font-primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --roc-font-size-h1: 48px;
  --roc-font-size-h2: 36px;
  --roc-font-size-h3: 24px;
  --roc-font-size-body: 16px;
  --roc-font-size-small: 14px;
  
  /* Espaciado (sistema base 8px) */
  --roc-space-xs: 4px;
  --roc-space-sm: 8px;
  --roc-space-md: 16px;
  --roc-space-lg: 24px;
  --roc-space-xl: 32px;
  --roc-space-2xl: 48px;
  
  /* Transiciones */
  --roc-transition-fast: 0.2s ease;
  --roc-transition-normal: 0.3s ease;
}
```

**Checklist Fase 1**:
- [ ] Crear estructura de directorios `assets/css/`
- [ ] Implementar `roc_variables.css` completo
- [ ] Implementar `roc_layout.css` con grid system
- [ ] Implementar `roc_components.css` base
- [ ] Validar CSS y probar herencia de variables
- [ ] Documentar todas las variables personalizadas

---

## 🔌 Fase 2: Integración con Streamlit (3-4 días)

### 2.1 Sistema de Inyección CSS

**Archivo**: `modules/ui/styles.py`

```python
"""Helper module for ROC Skincare styling injection in Streamlit."""

import streamlit as st
from pathlib import Path


def load_roc_styles():
    """Load and inject ROC Skincare CSS styles into Streamlit app."""
    
    css_dir = Path(__file__).parent.parent.parent / "assets" / "css"
    
    css_files = [
        "roc_variables.css",
        "roc_layout.css",
        "roc_components.css"
    ]
    
    combined_css = ""
    for css_file in css_files:
        css_path = css_dir / css_file
        if css_path.exists():
            with open(css_path, "r", encoding="utf-8") as f:
                combined_css += f"/* {css_file} */\n"
                combined_css += f.read() + "\n\n"
    
    st.markdown(f"<style>{combined_css}</style>", unsafe_allow_html=True)
```

### 2.2 Modificar app.py

```python
# Al inicio de app.py, después de imports
from modules.ui.styles import load_roc_styles

def main():
    st.set_page_config(
        page_title="Receipt Management System | ROC Skincare",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Cargar estilos ROC
    load_roc_styles()
    
    # ... resto del código
```

### 2.3 Componentes CSS Base

**Archivo**: `assets/css/roc_components.css`

```css
/* ========== BOTONES ========== */
.stButton > button {
  background-color: var(--roc-primary);
  color: var(--roc-white);
  padding: var(--roc-space-md) var(--roc-space-xl);
  font-size: var(--roc-font-size-small);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border: 2px solid var(--roc-primary);
  border-radius: 0;
  transition: all var(--roc-transition-normal);
  width: 100%;
}

.stButton > button:hover {
  background-color: transparent;
  color: var(--roc-primary);
}

/* ========== SIDEBAR ========== */
section[data-testid="stSidebar"] {
  background-color: var(--roc-primary);
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  color: var(--roc-gold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ========== MÉTRICAS ========== */
div[data-testid="stMetric"] {
  background: linear-gradient(135deg, var(--roc-primary) 0%, var(--roc-primary-dark) 100%);
  padding: var(--roc-space-lg);
  border-left: 4px solid var(--roc-gold);
}

div[data-testid="stMetric"] label {
  color: var(--roc-gold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
  color: var(--roc-white);
  font-weight: 700;
}
```

**Checklist Fase 2**:
- [ ] Crear módulo `ui/styles.py`
- [ ] Implementar función `load_roc_styles()`
- [ ] Modificar `app.py` para cargar estilos
- [ ] Estilizar botones con override de Streamlit
- [ ] Estilizar sidebar
- [ ] Estilizar métricas/estadísticas
- [ ] Estilizar formularios e inputs
- [ ] Probar integración sin errores

---

## 🎨 Fase 3: Componentes Avanzados (2-3 días)

### 3.1 Sistema de Badges

**Archivo**: `modules/ui/components.py`

```python
"""ROC Skincare UI Components"""

from enum import Enum


class BadgeVariant(Enum):
    DEFAULT = "default"
    NEW = "new"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


def roc_badge(text: str, variant: BadgeVariant = BadgeVariant.DEFAULT) -> str:
    """
    Generate ROC-styled badge HTML
    
    Args:
        text: Badge text
        variant: Badge style variant
    
    Returns:
        HTML string for badge
    """
    return f'<span class="roc-badge roc-badge--{variant.value}">{text}</span>'


def roc_card(title: str, content: str, badge: str = None) -> str:
    """
    Generate ROC-styled card HTML
    
    Args:
        title: Card title
        content: Card content (HTML)
        badge: Optional badge text
    
    Returns:
        HTML string for card
    """
    badge_html = f'<span class="roc-card__badge">{badge}</span>' if badge else ''
    
    return f"""
    <div class="roc-card">
        {badge_html}
        <div class="roc-card__header">
            <h3 class="roc-card__title">{title}</h3>
        </div>
        <div class="roc-card__content">
            {content}
        </div>
    </div>
    """
```

### 3.2 CSS para Badges y Cards

```css
/* ========== BADGES ========== */
.roc-badge {
  display: inline-block;
  padding: var(--roc-space-xs) var(--roc-space-sm);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border: 1px solid var(--roc-primary);
  background-color: var(--roc-white);
  color: var(--roc-primary);
}

.roc-badge--new {
  background-color: var(--roc-gold);
  border-color: var(--roc-gold);
  color: var(--roc-white);
}

.roc-badge--success {
  background-color: #28A745;
  border-color: #28A745;
  color: var(--roc-white);
}

/* ========== CARDS ========== */
.roc-card {
  background: var(--roc-white);
  border: 1px solid var(--roc-gray-medium);
  padding: var(--roc-space-lg);
  position: relative;
  transition: all var(--roc-transition-normal);
}

.roc-card:hover {
  box-shadow: 0 4px 12px rgba(0, 30, 43, 0.15);
  transform: translateY(-2px);
}

.roc-card__title {
  font-size: var(--roc-font-size-h3);
  font-weight: 700;
  color: var(--roc-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

### 3.3 Personalización de Gráficos

**Archivo**: `modules/ui/themes.py`

```python
"""ROC Skincare chart themes"""

ROC_CHART_THEME = {
    'layout': {
        'font': {
            'family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'size': 14,
            'color': '#001E2B'
        },
        'paper_bgcolor': '#FFFFFF',
        'plot_bgcolor': '#F5F5F5',
        'colorway': ['#001E2B', '#C6A052', '#8CA3B8', '#D4B77A'],
        'title': {
            'font': {'size': 24, 'color': '#001E2B'},
            'x': 0.5,
            'xanchor': 'center'
        }
    }
}


def apply_roc_theme(fig):
    """Apply ROC theme to Plotly figure"""
    fig.update_layout(**ROC_CHART_THEME['layout'])
    return fig
```

**Checklist Fase 3**:
- [ ] Crear módulo `ui/components.py`
- [ ] Implementar sistema de badges
- [ ] Implementar componente de cards
- [ ] Crear tema para gráficos Plotly
- [ ] Implementar loading spinner
- [ ] Crear componente de modal
- [ ] Documentar uso de componentes

---

## 📱 Fase 4: Responsive Design (1-2 días)

### 4.1 Breakpoints Mobile-First

**Archivo**: `assets/css/roc_layout.css`

```css
/* ========== RESPONSIVE BREAKPOINTS ========== */

/* Mobile (default - < 768px) */
@media (max-width: 767px) {
  :root {
    --roc-font-size-h1: 32px;
    --roc-font-size-h2: 28px;
    --roc-font-size-h3: 20px;
  }
  
  .main .block-container {
    padding: var(--roc-space-md) var(--roc-space-sm);
  }
  
  div[data-testid="column"] {
    width: 100% !important;
  }
  
  .stButton > button {
    width: 100%;
  }
}

/* Tablet (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1023px) {
  :root {
    --roc-font-size-h1: 40px;
    --roc-font-size-h2: 32px;
  }
  
  .roc-grid--4 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop (> 1024px) */
@media (min-width: 1024px) {
  .roc-container {
    max-width: 1440px;
  }
}
```

### 4.2 Touch Optimization

```css
/* ========== TOUCH TARGETS ========== */
@media (hover: none) and (pointer: coarse) {
  .stButton > button,
  .roc-badge {
    min-height: 44px;
    min-width: 44px;
  }
  
  .stButton > button:active {
    transform: scale(0.98);
  }
}
```

**Checklist Fase 4**:
- [ ] Implementar breakpoints responsive
- [ ] Probar en dispositivos móviles reales
- [ ] Verificar touch targets (44x44px mínimo)
- [ ] Probar sidebar en móvil
- [ ] Optimizar tablas para pantallas pequeñas
- [ ] Verificar orientación landscape/portrait

---

## ✅ Fase 5: Testing y QA (2-3 días)

### 5.1 Checklist de Accesibilidad (WCAG AA)

- [ ] Contraste de colores ≥ 4.5:1 para texto normal
- [ ] Contraste de colores ≥ 3:1 para texto grande
- [ ] Estados `:focus` visibles en todos los elementos
- [ ] Navegación completa por teclado
- [ ] Alt text en todas las imágenes
- [ ] Etiquetas ARIA donde sea necesario
- [ ] Pruebas con lector de pantalla (NVDA/JAWS)

### 5.2 Testing Cross-Browser

| Navegador | Versión | Estado |
|-----------|---------|--------|
| Chrome | Latest | ☐ |
| Firefox | Latest | ☐ |
| Safari | Latest | ☐ |
| Edge | Latest | ☐ |
| Mobile Safari | iOS 14+ | ☐ |
| Chrome Mobile | Android | ☐ |

### 5.3 Performance Targets

- [ ] CSS total < 150KB
- [ ] First Contentful Paint < 2s
- [ ] Time to Interactive < 3.5s
- [ ] Lighthouse Performance > 90
- [ ] Lighthouse Accessibility > 95

**Checklist Fase 5**:
- [ ] Audit de accesibilidad completo
- [ ] Testing en todos los navegadores objetivo
- [ ] Testing en dispositivos móviles
- [ ] Medición de performance
- [ ] Optimización de CSS (minificación)
- [ ] User acceptance testing
- [ ] Corrección de issues encontrados

---

## 📚 Fase 6: Documentación (1-2 días)

### 6.1 Component Library

**Crear**: `doc/ROC_COMPONENTS_LIBRARY.md`

Debe incluir:
- Catálogo de todos los componentes
- Ejemplos de código para cada uno
- Capturas de pantalla
- Props y parámetros
- Casos de uso recomendados

### 6.2 Maintenance Guide

**Crear**: `doc/ROC_MAINTENANCE_GUIDE.md`

Debe incluir:
- Cómo actualizar colores/estilos globales
- Cómo añadir nuevos componentes
- Convenciones de nomenclatura CSS
- Troubleshooting común
- Guía de contribución

**Checklist Fase 6**:
- [ ] Documentar todos los componentes
- [ ] Crear guía de mantenimiento
- [ ] Incluir ejemplos de código
- [ ] Capturar screenshots de componentes
- [ ] Documentar troubleshooting
- [ ] Actualizar README principal

---

## 📅 Plan de Ejecución

### Timeline Detallado

| Fase | Duración | Días | Prioridad |
|------|----------|------|-----------|
| **Fase 1: Design System Base** | 2-3 días | 1-3 | Alta |
| **Fase 2: Streamlit Integration** | 3-4 días | 4-7 | Alta |
| **Fase 3: Advanced Components** | 2-3 días | 8-10 | Media |
| **Fase 4: Responsive Design** | 1-2 días | 11-12 | Alta |
| **Fase 5: Testing & QA** | 2-3 días | 13-15 | Alta |
| **Fase 6: Documentation** | 1-2 días | 16 | Media |
| **TOTAL** | **11-16 días** | | |

### Desglose Semanal

**Semana 1 (Días 1-5)**
- Día 1: Setup y variables CSS
- Día 2: Layout system
- Día 3: Componentes básicos
- Día 4: Integración Streamlit
- Día 5: Completar componentes base

**Semana 2 (Días 6-10)**
- Días 6-7: Estilizar páginas (Dashboard, Processor)
- Días 8-9: Componentes avanzados
- Día 10: Testing de componentes

**Semana 3 (Días 11-16)**
- Días 11-12: Responsive y mobile
- Días 13-14: Testing y QA
- Día 15: Correcciones
- Día 16: Documentación y deployment

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Conflictos CSS con Streamlit** | Alta | Alto | Usar selectores de alta especificidad, probar early |
| **Incompatibilidad navegadores** | Media | Medio | Testing cross-browser desde el inicio |
| **Performance degradation** | Baja | Alto | Minificar CSS, lazy loading |
| **Responsive no funciona** | Media | Alto | Mobile-first approach, probar en dispositivos reales |
| **Delays en timeline** | Media | Medio | Buffer de 20% en estimaciones, priorizar features |

### Estrategias de Mitigación

1. **Override CSS de Streamlit**:
   ```css
   /* Usar selectores específicos */
   section[data-testid="stSidebar"] .stButton > button {
     /* estilos */
   }
   
   /* Usar !important solo cuando sea necesario */
   background-color: var(--roc-primary) !important;
   ```

2. **Fallbacks para navegadores**:
   ```css
   .roc-card {
     background: #FFFFFF; /* Fallback */
     background: var(--roc-white); /* Modern */
   }
   ```

3. **Performance Budget**:
   - CSS total: < 150KB
   - Parse time: < 50ms
   - No unused CSS > 20%

---

## 📊 Métricas de Éxito

### KPIs Técnicos

| Métrica | Target | Herramienta |
|---------|--------|-------------|
| CSS File Size | < 150KB | File analysis |
| First Contentful Paint | < 2s | Lighthouse |
| Time to Interactive | < 3.5s | Lighthouse |
| Accessibility Score | > 95/100 | Lighthouse, axe |
| Browser Compatibility | 100% | Manual testing |

### KPIs de Usuario

| Métrica | Target | Método |
|---------|--------|--------|
| User Satisfaction | > 4/5 | Survey |
| Task Completion | > 95% | User testing |
| Error Rate | < 2% | Analytics |

### Criterios de Aceptación

**Debe cumplir (Critical)**:
- [ ] Colores ROC implementados correctamente
- [ ] Tipografía coincide con guía de estilos
- [ ] Responsive funciona en mobile/tablet/desktop
- [ ] WCAG AA compliance
- [ ] Funciona en Chrome, Firefox, Safari, Edge
- [ ] Sin regresiones funcionales
- [ ] Performance targets alcanzados

**Debería cumplir (Important)**:
- [ ] Componentes avanzados implementados
- [ ] Gráficos con tema ROC
- [ ] Animaciones y transiciones
- [ ] Documentación completa

---

## 📝 Notas de Implementación

### Consideraciones Técnicas

1. **Streamlit CSS Overrides**:
   - Streamlit usa IDs dinámicos
   - Usar `data-testid` en selectores
   - Documentar uso de `!important`

2. **BEM Naming Convention**:
   ```css
   .roc-component { }           /* Block */
   .roc-component__element { }  /* Element */
   .roc-component--modifier { } /* Modifier */
   ```

3. **CSS Variable Usage**:
   ```css
   /* Siempre usar variables */
   color: var(--roc-primary);
   
   /* Evitar hard-coding */
   color: #001E2B;
   ```

### Best Practices

- Mobile-first approach
- Progressive enhancement
- Graceful degradation
- Semantic HTML
- Accessibility first
- Performance optimization
- Documentation throughout

---

## 🚀 Próximos Pasos

### Pre-Implementación

1. **Aprobación**:
   - [ ] Revisar este plan con stakeholders
   - [ ] Aprobar timeline y recursos
   - [ ] Sign-off de diseño

2. **Setup**:
   - [ ] Crear branch: `feature/roc-styling`
   - [ ] Backup de aplicación actual
   - [ ] Crear estructura de directorios
   - [ ] Instalar herramientas de testing

3. **Kickoff**:
   - [ ] Meeting de inicio
   - [ ] Asignar desarrollador
   - [ ] Setup de tracking
   - [ ] Primera iteración (Día 1)

### Durante Implementación

- **Daily**: Standup de 15 minutos
- **Weekly**: Demo los viernes
- **Continuous**: Commits frecuentes, testing

### Post-Implementación

- **Code Review** antes de merge
- **QA Sign-off**
- **Deploy a staging**
- **User testing**
- **Deploy a producción**

---

## 📎 Recursos

### Documentación
- [Roc skincare style.txt](Roc%20skincare%20style.txt) - Guía fuente
- [Streamlit Docs](https://docs.streamlit.io/) - Documentación oficial
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/) - Accesibilidad

### Herramientas
- Chrome DevTools - Testing y debug
- Lighthouse - Performance y accesibilidad
- axe DevTools - Accesibilidad
- WAVE - Web accessibility
- BrowserStack - Cross-browser (opcional)

### Referencia
- Sitio ROC: https://www.rocskincare.com/
- MDN Web Docs: https://developer.mozilla.org/
- CSS-Tricks: https://css-tricks.com/

---

## 📋 Anexos

### A. Paleta de Colores

| Color | Hex | RGB | Uso |
|-------|-----|-----|-----|
| Primary | #001E2B | 0,30,43 | Botones, headers |
| Primary Dark | #00161F | 0,22,31 | Hover states |
| Gold | #C6A052 | 198,160,82 | Acentos, CTAs |
| Gold Light | #D4B77A | 212,183,122 | Hover gold |
| White | #FFFFFF | 255,255,255 | Backgrounds |
| Gray Light | #F5F5F5 | 245,245,245 | Alt backgrounds |
| Gray Medium | #E8E8E8 | 232,232,232 | Borders |

### B. Tipografía

| Elemento | Tamaño | Peso | Transform |
|----------|--------|------|-----------|
| H1 | 48px | 700 | UPPERCASE |
| H2 | 36px | 700 | UPPERCASE |
| H3 | 24px | 500 | UPPERCASE |
| Body | 16px | 400 | None |
| Small | 14px | 400 | None |

### C. Espaciado

| Token | Valor | Uso |
|-------|-------|-----|
| xs | 4px | Tight spacing |
| sm | 8px | Form elements |
| md | 16px | Standard |
| lg | 24px | Sections |
| xl | 32px | Large sections |
| 2xl | 48px | Page sections |

---

**Última actualización**: Enero 29, 2026  
**Versión**: 1.0  
**Estado**: 📝 Planificado  
**Próxima revisión**: Al iniciar implementación

---

**FIN DEL PLAN DE IMPLEMENTACIÓN**
