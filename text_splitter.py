"""
Text Splitter Module - Corte inteligente de texto em blocos de 2500 caracteres
Respeita pontos finais, detecta problemas potenciais (números cortados, listas)
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TextBlock:
    """Representa um bloco de texto cortado"""
    id: int
    content: str
    char_count: int
    warnings: List[str]
    start_pos: int  # Posição original no texto
    end_pos: int


@dataclass
class SplitResult:
    """Resultado do corte de texto"""
    blocks: List[TextBlock]
    total_chars: int
    total_blocks: int


class TextSplitter:
    """
    Divide texto em blocos de tamanho máximo respeitando pontos finais.
    Detecta possíveis problemas como números cortados e listas numeradas.
    """
    
    def __init__(self, max_chars: int = 2500):
        self.max_chars = max_chars
        
        # Padrões para detectar problemas
        self.patterns = {
            # Número decimal cortado no início (ex: ",99" ou ".99")
            'number_start': re.compile(r'^[\s]*[,\.]\d+'),
            # Número decimal cortado no fim (ex: "25." ou "25,")
            'number_end': re.compile(r'\d+[,\.]\s*$'),
            # Lista numerada no fim (ex: "1." ou "2.")
            'list_end': re.compile(r'\n\s*\d+\.\s*$'),
            # Palavra cortada (termina com hífen)
            'word_cut': re.compile(r'-\s*$'),
            # Abreviação cortada (ex: "Dr." "Sr." "etc.")
            'abbrev_end': re.compile(r'\b(Dr|Sr|Sra|Jr|etc|ex|fig|pág|vol|cap|art|nº|n°)\.\s*$', re.IGNORECASE),
        }
    
    def split(self, text: str) -> SplitResult:
        """
        Divide o texto em blocos de até max_chars caracteres.
        
        Args:
            text: Texto completo para dividir
            
        Returns:
            SplitResult com lista de blocos e metadados
        """
        if not text or not text.strip():
            return SplitResult(blocks=[], total_chars=0, total_blocks=0)
        
        # Normaliza quebras de linha
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        blocks = []
        current_pos = 0
        block_id = 1
        
        while current_pos < len(text):
            # Pega um chunk do tamanho máximo
            end_pos = min(current_pos + self.max_chars, len(text))
            chunk = text[current_pos:end_pos]
            
            # Se não é o último bloco, encontra o melhor ponto de corte
            if end_pos < len(text):
                cut_pos = self._find_best_cut(chunk)
                chunk = chunk[:cut_pos]
                end_pos = current_pos + cut_pos
            
            # Detecta problemas no bloco
            warnings = self._detect_warnings(chunk, text, current_pos, end_pos)
            
            # Cria o bloco
            block = TextBlock(
                id=block_id,
                content=chunk.strip(),
                char_count=len(chunk.strip()),
                warnings=warnings,
                start_pos=current_pos,
                end_pos=end_pos
            )
            blocks.append(block)
            
            current_pos = end_pos
            block_id += 1
        
        return SplitResult(
            blocks=blocks,
            total_chars=len(text),
            total_blocks=len(blocks)
        )
    
    def _find_best_cut(self, chunk: str) -> int:
        """
        Encontra o melhor ponto de corte no chunk.
        Prioridade: parágrafo > ponto final > vírgula > espaço
        """
        # Tenta encontrar quebra de parágrafo
        para_match = chunk.rfind('\n\n')
        if para_match > len(chunk) * 0.5:  # Pelo menos 50% do chunk
            return para_match + 2
        
        # Tenta encontrar ponto final seguido de espaço ou quebra
        for i in range(len(chunk) - 1, int(len(chunk) * 0.5), -1):
            if chunk[i] == '.' and i + 1 < len(chunk) and chunk[i + 1] in ' \n':
                # Verifica se não é número decimal ou abreviação
                if not self._is_number_or_abbrev(chunk, i):
                    return i + 1
        
        # Tenta encontrar vírgula seguida de espaço
        for i in range(len(chunk) - 1, int(len(chunk) * 0.5), -1):
            if chunk[i] == ',' and i + 1 < len(chunk) and chunk[i + 1] == ' ':
                # Verifica se não é número decimal
                if i > 0 and not chunk[i-1].isdigit():
                    return i + 1
        
        # Último recurso: espaço mais próximo do final
        space_pos = chunk.rfind(' ')
        if space_pos > len(chunk) * 0.5:
            return space_pos + 1
        
        # Se nada funcionar, corta no limite
        return len(chunk)
    
    def _is_number_or_abbrev(self, text: str, dot_pos: int) -> bool:
        """Verifica se o ponto é parte de um número decimal ou abreviação"""
        # Verifica número decimal (ex: 25.99)
        if dot_pos > 0 and text[dot_pos - 1].isdigit():
            if dot_pos + 1 < len(text) and text[dot_pos + 1].isdigit():
                return True
        
        # Verifica abreviações comuns
        abbrevs = ['dr', 'sr', 'sra', 'jr', 'etc', 'ex', 'fig', 'pág', 'vol', 'cap', 'art', 'nº', 'n°']
        for abbrev in abbrevs:
            start = dot_pos - len(abbrev)
            if start >= 0:
                word = text[start:dot_pos].lower()
                if word == abbrev:
                    return True
        
        return False
    
    def _detect_warnings(self, chunk: str, full_text: str, start: int, end: int) -> List[str]:
        """Detecta possíveis problemas no bloco"""
        warnings = []
        
        # Verifica início do bloco
        if self.patterns['number_start'].match(chunk):
            warnings.append("⚠️ Possível número cortado no início (ex: ',99' deveria ser '25,99')")
        
        # Verifica fim do bloco
        if self.patterns['number_end'].search(chunk):
            warnings.append("⚠️ Possível número cortado no final (ex: '25,' pode continuar com '99')")
        
        if self.patterns['list_end'].search(chunk):
            warnings.append("⚠️ Lista numerada pode estar cortada (título separado do conteúdo)")
        
        if self.patterns['word_cut'].search(chunk):
            warnings.append("⚠️ Palavra pode estar cortada (termina com hífen)")
        
        if self.patterns['abbrev_end'].search(chunk):
            warnings.append("⚠️ Abreviação pode estar cortada no final")
        
        # Verifica se o próximo bloco começa de forma suspeita
        if end < len(full_text):
            next_start = full_text[end:end+20]
            if re.match(r'^[\s]*[,\.]\d', next_start):
                warnings.append("⚠️ Próximo bloco inicia com continuação de número")
        
        return warnings
    
    def merge_blocks(self, blocks: List[TextBlock], indices: List[int]) -> List[TextBlock]:
        """
        Mescla múltiplos blocos em um só.
        
        Args:
            blocks: Lista de todos os blocos
            indices: Índices dos blocos a mesclar (devem ser consecutivos)
        """
        if not indices or len(indices) < 2:
            return blocks
        
        indices = sorted(indices)
        
        # Verifica se são consecutivos
        for i in range(len(indices) - 1):
            if indices[i + 1] - indices[i] != 1:
                raise ValueError("Blocos devem ser consecutivos para mesclar")
        
        # Mescla o conteúdo
        merged_content = ' '.join(blocks[i].content for i in indices)
        
        # Cria novo bloco
        new_block = TextBlock(
            id=blocks[indices[0]].id,
            content=merged_content,
            char_count=len(merged_content),
            warnings=[],  # Recalcular se necessário
            start_pos=blocks[indices[0]].start_pos,
            end_pos=blocks[indices[-1]].end_pos
        )
        
        # Recria lista de blocos
        new_blocks = []
        skip_until = -1
        for i, block in enumerate(blocks):
            if i in indices:
                if i == indices[0]:
                    new_blocks.append(new_block)
                # Pula os outros
            else:
                new_blocks.append(block)
        
        # Renumera
        for i, block in enumerate(new_blocks):
            block.id = i + 1
        
        return new_blocks


def split_text(text: str, max_chars: int = 2500) -> SplitResult:
    """Função de conveniência para dividir texto"""
    splitter = TextSplitter(max_chars=max_chars)
    return splitter.split(text)


# Teste rápido
if __name__ == "__main__":
    test_text = """
    Este é um texto de exemplo para testar o sistema de corte.
    
    1. Primeiro item da lista
    Este é o conteúdo do primeiro item com bastante texto para preencher.
    
    2. Segundo item
    O capital total é de 25.980,99 dólares no banco para investimento.
    
    Dr. Silva disse que o procedimento seria às 14h30.
    
    Continuando com mais texto para testar os cortes automáticos.
    """ * 20  # Multiplica para ter texto longo
    
    result = split_text(test_text)
    
    print(f"Total de caracteres: {result.total_chars}")
    print(f"Total de blocos: {result.total_blocks}")
    print()
    
    for block in result.blocks:
        print(f"--- Bloco {block.id} ({block.char_count} chars) ---")
        print(f"Conteúdo: {block.content[:100]}...")
        if block.warnings:
            for warning in block.warnings:
                print(f"  {warning}")
        print()
