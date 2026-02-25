import os
import uuid
import httpx
from io import BytesIO
from fastapi import UploadFile, HTTPException, status
from PIL import Image

async def process_and_validate_image(image: UploadFile, subfolder: str) -> str:
    """
    Lê a imagem, converte para RGB (JPEG) e faz o upload direto para o Supabase Storage.
    Retorna a URL pública completa da imagem.
    """
    try:
        # 1. Lê a imagem e otimiza para JPEG (economiza armazenamento)
        content = await image.read()
        image_stream = BytesIO(content)
        pil_image = Image.open(image_stream).convert("RGB")
        
        output_buffer = BytesIO()
        pil_image.save(output_buffer, format="JPEG", quality=85)
        output_buffer.seek(0)
        
        # 2. Configurações e caminhos
        new_filename = f"{uuid.uuid4()}.jpg"
        file_path = f"{subfolder}/{new_filename}"  # Ex: users/uuid.jpg
        bucket_name = "bolao"
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            # Fallback para caso você esteja testando localmente sem as chaves
            print("AVISO: Chaves do Supabase ausentes. Usando fallback.")
            return f"/uploads/{file_path}"

        # 3. Upload ultra-rápido via API REST do Supabase (Usando o HTTPX que já temos)
        upload_url = f"{supabase_url}/storage/v1/object/{bucket_name}/{file_path}"
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "image/jpeg"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(upload_url, headers=headers, content=output_buffer.read())
            
            if response.status_code not in (200, 201):
                print(f"Erro Supabase: {response.text}")
                raise HTTPException(status_code=500, detail="Erro ao enviar imagem para a nuvem.")
                
        # 4. Retorna a URL pública final para salvar no banco de dados!
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
        return public_url

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erro no processamento da imagem: {e}")
        raise HTTPException(status_code=400, detail="Erro ao processar formato da imagem.")