import os
import uuid
from io import BytesIO
from fastapi import UploadFile, HTTPException, status
from PIL import Image

async def process_and_validate_image(image: UploadFile, subfolder: str) -> str:
    """
    Lê a imagem, converte para RGB e salva no disco.
    A validação NSFW foi desativada para economizar memória no servidor.
    Retorna o caminho relativo para salvar no banco.
    
    Args:
        image: O arquivo enviado via UploadFile
        subfolder: A pasta dentro de 'uploads/' onde salvar (ex: 'teams' ou 'users')
    """
    
    # Define o diretório base de uploads
    base_upload_dir = "uploads"
    target_dir = os.path.join(base_upload_dir, subfolder)
    
    # Cria a pasta se não existir
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    try:
        # 1. Ler o arquivo
        content = await image.read()
        image_stream = BytesIO(content)
        
        # 2. Validar Imagem (Integridade + Conversão RGB)
        # Importante: .convert("RGB") evita erro com imagens Grayscale ou PNGs transparentes
        pil_image = Image.open(image_stream).convert("RGB")
        
        # 3. Salvar Arquivo
        # Forçamos a extensão .jpg ou mantemos a original se for segura
        file_ext = os.path.splitext(image.filename)[1] or ".jpg"
        new_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Caminho físico
        file_path = os.path.join(target_dir, new_filename)
        
        # Escreve os bytes no disco
        with open(file_path, "wb+") as buffer:
            buffer.write(content)
            
        # Retorna URL relativa para o banco (ex: /uploads/users/foto.jpg)
        # Importante usar barras normais para URL
        return f"/uploads/{subfolder}/{new_filename}"

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erro no processamento da imagem: {e}")
        raise HTTPException(status_code=400, detail="Erro ao processar a imagem. Verifique o formato.")