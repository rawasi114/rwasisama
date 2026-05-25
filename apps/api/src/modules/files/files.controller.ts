import {
  Controller,
  Delete,
  Get,
  Param,
  ParseUUIDPipe,
  Post,
  Res,
  UploadedFile,
  UseGuards,
  UseInterceptors,
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiBearerAuth, ApiConsumes, ApiTags } from '@nestjs/swagger';
import { Response } from 'express';
import { PoliciesGuard } from '../../common/guards/policies.guard';
import { CheckPolicies } from '../../common/decorators/check-policies.decorator';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { FilesService } from './files.service';

interface MulterFile {
  originalname: string;
  mimetype: string;
  buffer: Buffer;
  size: number;
}

@ApiTags('files')
@ApiBearerAuth()
@UseGuards(PoliciesGuard)
@Controller('files')
export class FilesController {
  constructor(private readonly filesService: FilesService) {}

  @Post()
  @ApiConsumes('multipart/form-data')
  @CheckPolicies((a) => a.can('create', 'File'))
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: 25 * 1024 * 1024 } }))
  async upload(
    @UploadedFile() file: MulterFile,
    @CurrentUser('id') userId: string,
  ) {
    if (!file) {
      throw new BadRequestException('لم يتم إرفاق ملف');
    }
    const record = await this.filesService.upload({
      originalName: file.originalname,
      mimeType: file.mimetype,
      data: file.buffer,
      uploadedById: userId,
    });
    return { id: record.id, originalName: record.originalName, sizeBytes: record.sizeBytes };
  }

  @Get(':id')
  @CheckPolicies((a) => a.can('read', 'File'))
  getMetadata(@Param('id', ParseUUIDPipe) id: string) {
    return this.filesService.getByIdOrFail(id);
  }

  @Get(':id/download')
  @CheckPolicies((a) => a.can('read', 'File'))
  async download(@Param('id', ParseUUIDPipe) id: string, @Res() res: Response) {
    const { file, data } = await this.filesService.download(id);
    res.setHeader('Content-Type', file.mimeType);
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${encodeURIComponent(file.originalName)}"`,
    );
    res.send(data);
  }

  @Delete(':id')
  @CheckPolicies((a) => a.can('delete', 'File'))
  async remove(@Param('id', ParseUUIDPipe) id: string) {
    await this.filesService.remove(id);
    return { success: true };
  }
}
