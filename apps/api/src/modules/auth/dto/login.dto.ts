import { IsEmail, IsString, MinLength } from 'class-validator';

export class LoginDto {
  @IsEmail({}, { message: 'بريد إلكتروني غير صالح' })
  email!: string;

  @IsString()
  @MinLength(1, { message: 'كلمة المرور مطلوبة' })
  password!: string;
}
