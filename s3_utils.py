# s3_utils.py
import base64, boto3, os
from botocore.exceptions import ClientError

AWS_REGION=os.environ.get("AWS_REGION")
AWS_ACCESS_KEY_ID=os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=os.environ.get("AWS_SECRET_ACCESS_KEY")
S3_URL = os.environ.get("S3_URL")
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_PUBLIC = os.getenv("S3_PUBLIC", "true").lower() == "true"

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
)

def upload_audio_base64(base64_str: str, key: str) -> str:
    """
    base64 mp3를 S3에 업로드. 성공 시 s3:// 경로(또는 정적 URL 경로) 반환
    """
    try:
        audio_bytes = base64.b64decode(base64_str)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,                   # 예: f"chatrooms/results/{chatroom_id}/letter_voice.mp3"
            Body=audio_bytes,
            ContentType="audio/mpeg",  # 중요: 브라우저 재생용
            ACL="public-read",       # 퍼블릭로 만들려면 주석 해제 (버킷 정책 허용 필요)
            # ServerSideEncryption="AES256",  # 원하면 서버측 암호화
        )
        # 정적 URL 형식 (버킷이 퍼블릭 읽기이면 바로 접근 가능)
        return f"https://{S3_BUCKET}.s3.ap-northeast-2.amazonaws.com/{key}"
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")

def create_presigned_url(key: str, expires: int = 3600) -> str:
    """
    비공개 버킷일 때, 제한 시간 있는 접근 URL 발급
    """
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
