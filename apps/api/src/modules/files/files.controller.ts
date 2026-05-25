import {
  BadRequestException,
  Controller,
  Get,
  Param,
  Post,
  Res,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiBearerAuth, ApiConsumes, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Response } from 'express';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { RequirePermission } from '../../common/decorators/require-permission.decorator';
import { FilesService } from './files.service';

@ApiTags('files')
@ApiBearerAuth()
@Controller('files')
export class FilesController {
  constructor(private readonly files: FilesService) {}

  @Post()
  @RequirePermission('file', 'create')
  @ApiConsumes('multipart/form-data')
  @ApiOperation({ summary: 'رفع ملف' })
  @UseInterceptors(FileInterceptor('file'))
  upload(@UploadedFile() file: Express.Multer.File, @CurrentUser('id') userId: string) {
    if (!file) throw new BadRequestException('لم يتم إرفاق ملف');
    return this.files.upload(file, userId);
  }

  @Get(':id')
  @RequirePermission('file', 'read')
  @ApiOperation({ summary: 'بيانات ملف' })
  meta(@Param('id') id: string) {
    return this.files.getMeta(id);
  }

  @Get(':id/download')
  @RequirePermission('file', 'read')
  @ApiOperation({ summary: 'تنزيل ملف' })
  async download(@Param('id') id: string, @Res() res: Response) {
    const { meta, buffer } = await this.files.download(id);
    res.setHeader('Content-Type', meta.mimeType);
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${encodeURIComponent(meta.originalName)}"`,
    );
    res.send(buffer);
  }
}
