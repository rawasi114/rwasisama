import { IsString, MinLength } from 'class-validator';

export class RefreshDto {
  @IsString()
  @MinLength(10, { message: 'رمز التحديث مطلوب' })
  refreshToken!: string;
}
