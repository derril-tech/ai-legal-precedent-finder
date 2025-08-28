import {
  Controller,
  Post,
  Body,
  Param,
  Get,
  UseGuards,
  Request,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { ExportsService } from './exports.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CreateExportDto } from './dto/create-export.dto';

@ApiTags('exports')
@Controller('exports')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class ExportsController {
  constructor(private readonly exportsService: ExportsService) {}

  @Post('brief')
  @ApiOperation({ summary: 'Generate legal brief export' })
  @ApiResponse({ status: 201, description: 'Brief generated successfully' })
  async generateBrief(
    @Body() createExportDto: CreateExportDto,
    @Request() req: any,
  ) {
    return this.exportsService.generateBrief(
      createExportDto.session_id,
      req.user.workspaceId,
    );
  }

  @Post('citations')
  @ApiOperation({ summary: 'Generate citation table export' })
  @ApiResponse({ status: 201, description: 'Citation table generated successfully' })
  async generateCitationTable(
    @Body() createExportDto: CreateExportDto,
    @Request() req: any,
  ) {
    return this.exportsService.generateCitationTable(
      createExportDto.session_id,
      req.user.workspaceId,
    );
  }

  @Post('json')
  @ApiOperation({ summary: 'Generate JSON bundle export' })
  @ApiResponse({ status: 201, description: 'JSON bundle generated successfully' })
  async generateJsonBundle(
    @Body() createExportDto: CreateExportDto,
    @Request() req: any,
  ) {
    return this.exportsService.generateJsonBundle(
      createExportDto.session_id,
      req.user.workspaceId,
    );
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get export by ID' })
  @ApiResponse({ status: 200, description: 'Export retrieved successfully' })
  async getExport(@Param('id') id: string, @Request() req: any) {
    return this.exportsService.getExport(id, req.user.workspaceId);
  }

  @Get(':id/download')
  @ApiOperation({ summary: 'Get export download URL' })
  @ApiResponse({ status: 200, description: 'Download URL generated' })
  async getExportDownloadUrl(@Param('id') id: string, @Request() req: any) {
    return this.exportsService.getExportDownloadUrl(id, req.user.workspaceId);
  }
}
