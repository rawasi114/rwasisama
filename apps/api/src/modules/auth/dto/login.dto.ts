import { ApiProperty } from '@nestjs/swagger';
import { IsEmail, IsString, MinLength } from 'class-validator';

export class LoginDto {
  @ApiProperty({ example: 'admin@rawasi-sama.sa' })
  @IsEmail({}, { message: 'البريد الإلكتروني غير صالح' })
  email!: string;

  @ApiProperty({ example: 'Admin@12345' })
  @IsString()
  @MinLength(8, { message: 'كلمة المرور يجب ألا تقل عن 8 أحرف' })
  password!: string;
}
