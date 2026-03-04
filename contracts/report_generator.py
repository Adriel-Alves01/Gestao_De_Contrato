"""
Gerador de relatórios em PDF para contratos.

Responsável por:
- Gerar PDF individual de um contrato
- Incluir dados completos (contrato, medições, pagamentos)
- Layout profissional e formatação
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.enums import TA_CENTER


class ContractReportGenerator:
    """Gerador de relatórios PDF para contratos."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define estilos customizados para o relatório."""
        # Título
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Seção
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#283593'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        ))

        # Label normal
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4
        ))

    def generate_contract_report(self, contract, output_path=None):
        """
        Gera relatório PDF de um contrato.

        Args:
            contract: Instância do modelo Contract
            output_path: Caminho para salvar o PDF (opcional)

        Returns:
            BytesIO: Buffer com conteúdo do PDF (se output_path não fornecido)
        """
        # Se não forneceu path, usa BytesIO
        if output_path is None:
            pdf_buffer = BytesIO()
            pdf_file = pdf_buffer
        else:
            pdf_file = output_path

        # Cria documento PDF
        doc = SimpleDocTemplate(
            pdf_file,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title=f"Contrato {contract.id}",
            author="GestãoContrato"
        )

        # Constrói conteúdo
        story = []
        story.extend(self._build_header(contract))
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._build_contract_info(contract))
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_measurements_table(contract))
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_payments_table(contract))
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_footer(contract))

        # Constrói PDF
        doc.build(story)

        # Se usou BytesIO, retorna o buffer
        if output_path is None:
            pdf_buffer.seek(0)
            return pdf_buffer

        return pdf_file

    def _build_header(self, contract):
        """Constrói cabeçalho do relatório."""
        elements = []

        # Título
        title = Paragraph(
            "RELATÓRIO DE CONTRATO",
            self.styles['CustomTitle']
        )
        elements.append(title)

        # Informações básicas em linha
        info_text = f"""
        <b>Contrato ID:</b> {contract.id} |
        <b>Status:</b> {contract.get_status_display()} |
        <b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        elements.append(Paragraph(info_text, self.styles['Normal']))

        return elements

    def _build_contract_info(self, contract):
        """Constrói seção de informações do contrato."""
        elements = []

        # Título da seção
        elements.append(
            Paragraph("DADOS DO CONTRATO", self.styles['SectionTitle'])
        )

        # Dados gerais
        data = [
            ['Campo', 'Valor'],
            ['Título', contract.title],
            [
                'Gestor Responsável',
                contract.manager.get_full_name() or
                contract.manager.username
            ],
            ['Data Início', contract.start_date.strftime('%d/%m/%Y')],
            ['Data Fim', contract.end_date.strftime('%d/%m/%Y')],
            ['Descrição', contract.description or '---'],
        ]

        table = Table(data, colWidths=[2.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            (
                'ROWBACKGROUNDS',
                (0, 1), (-1, -1),
                [colors.white, colors.HexColor('#f5f5f5')]
            ),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))

        elements.append(table)

        # Valores financeiros
        elements.append(Spacer(1, 0.15*inch))
        valor_data = [
            [
                'Conceito',
                f"R$ {contract.total_value:,.2f}".replace(
                    ',', '@'
                ).replace('.', ',').replace('@', '.')
            ],
            [
                'Saldo Restante',
                f"R$ {contract.remaining_balance:,.2f}".replace(
                    ',', '@'
                ).replace('.', ',').replace('@', '.')
            ],
            [
                'Consumido (%)',
                f"{(
                    1 - (contract.remaining_balance / contract.total_value)
                    if contract.total_value > 0 else 0
                ) * 100:.1f}%"
            ],
        ]

        valor_labels = [
            'Valor Total', 'Saldo Restante', 'Percentual Consumido'
        ]
        valor_data_display = [
            [valor_labels[i], valor_data[i][1]] for i in range(3)
        ]

        valor_table = Table(
            valor_data_display,
            colWidths=[2.5*inch, 3.5*inch]
        )
        valor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8eaf6')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (5, 5), (-5, -5), 5),
        ]))

        elements.append(valor_table)

        return elements

    def _build_measurements_table(self, contract):
        """Constrói tabela de medições."""
        elements = []

        elements.append(Paragraph("MEDIÇÕES", self.styles['SectionTitle']))

        measurements = contract.measurements.all().order_by('-created_at')

        if not measurements:
            elements.append(Paragraph(
                "Nenhuma medição registrada.",
                self.styles['CustomNormal']
            ))
            return elements

        # Dados da tabela
        data = [['ID', 'Data', 'Valor', 'Status', 'Descrição']]

        for m in measurements:
            data.append([
                str(m.id),
                m.created_at.strftime('%d/%m/%Y'),
                f"R$ {m.value:,.2f}".replace(
                    ',', '@'
                ).replace('.', ',').replace('@', '.'),
                m.get_status_display(),
                (
                    m.description[:20] + '...'
                    if len(m.description) > 20
                    else m.description
                ),
            ])

        table = Table(
            data, colWidths=[0.6*inch, 1.2*inch, 1.2*inch, 1.2*inch, 2*inch]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            (
                'ROWBACKGROUNDS',
                (0, 1), (-1, -1),
                [colors.white, colors.HexColor('#f5f5f5')]
            ),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (4, 0), (4, -1), 'LEFT'),
        ]))

        elements.append(table)

        return elements

    def _build_payments_table(self, contract):
        """Constrói tabela de pagamentos."""
        elements = []

        elements.append(Paragraph("PAGAMENTOS", self.styles['SectionTitle']))

        payments = contract.payments.all().order_by('-created_at')

        if not payments:
            elements.append(Paragraph(
                "Nenhum pagamento registrado.",
                self.styles['CustomNormal']
            ))
            return elements

        # Dados da tabela
        data = [['ID', 'Medição', 'Data', 'Valor', 'Status']]

        for p in payments:
            data.append([
                str(p.id),
                str(p.measurement.id),
                p.created_at.strftime('%d/%m/%Y'),
                f"R$ {p.amount:,.2f}".replace(
                    ',', '@'
                ).replace('.', ',').replace('@', '.'),
                p.get_status_display(),
            ])

        table = Table(
            data,
            colWidths=[0.6*inch, 1*inch, 1.2*inch, 1.2*inch, 1.2*inch]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            (
                'ROWBACKGROUNDS',
                (0, 1), (-1, -1),
                [colors.white, colors.HexColor('#f5f5f5')]
            ),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)

        return elements

    def _build_footer(self, contract):
        """Constrói rodapé do relatório."""
        elements = []

        footer_text = f"""
        <b>Observações:</b><br/>
        Este relatório foi gerado automaticamente pelo sistema
        GestãoContrato.<br/>
        Contém informações confidenciais e restritas. Data: {
            datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
        }
        """

        elements.append(Paragraph(footer_text, self.styles['Normal']))

        return elements
