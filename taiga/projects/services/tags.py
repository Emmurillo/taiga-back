# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2016 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2016 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2016 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import connection

def tag_exist_for_project_elements(project, tag):
    return tag in dict(project.tags_colors).keys()


def create_tag(project, tag, color):
    project.tags_colors.append([tag, color])
    project.save()


def update_color_tag(project, tag, color):
    sql = """
        WITH
            -- Temporal table with two columns: project_id and tags_colors
            tags_colors AS (
            	SELECT id project_id, reduce_dim(tags_colors) tags_colors
                FROM projects_project
                WHERE id = {project_id}
            ),
            -- Temporal table with two columns: tag and color with the updated color
            expanded_tags_colors AS (
            	SELECT project_id, tags_colors[1] tag, tags_colors[2] color
            	FROM tags_colors
            	WHERE tags_colors[1] != '{tag}'
            	UNION
            	SELECT {project_id}, '{tag}' tag, '{color}' color
            ),
            rebuilt_tags_colors AS (
            	SELECT expanded_tags_colors.project_id project_id, array_agg_mult(ARRAY[[expanded_tags_colors.tag, expanded_tags_colors.color]]) tags_colors
            	FROM expanded_tags_colors
            	GROUP BY expanded_tags_colors.project_id
            )

        UPDATE projects_project
        SET tags_colors = rebuilt_tags_colors.tags_colors
        FROM rebuilt_tags_colors
        WHERE projects_project.id = rebuilt_tags_colors.project_id;
    """
    sql = sql.format(project_id=project.id, tag=tag, color=color)
    cursor = connection.cursor()
    cursor.execute(sql)


def rename_tag(project, from_tag, to_tag):
    color = dict(project.tags_colors)[from_tag]
    sql = """
        UPDATE userstories_userstory SET tags = array_distinct(array_replace(tags, '{from_tag}', '{to_tag}')) WHERE project_id={project_id};
        UPDATE tasks_task SET tags = array_distinct(array_replace(tags, '{from_tag}', '{to_tag}')) WHERE project_id={project_id};
        UPDATE issues_issue SET tags = array_distinct(array_replace(tags, '{from_tag}', '{to_tag}')) WHERE project_id={project_id};

        WITH
            tags_colors AS (
            	SELECT id project_id, reduce_dim(tags_colors) tags_colors
                FROM projects_project
                WHERE id = {project_id}
            ),
            expanded_tags_colors AS (
                SELECT project_id, tags_colors[1] tag, tags_colors[2] color
                FROM tags_colors
                WHERE tags_colors[1] != '{from_tag}'
                UNION
                SELECT {project_id} project_id, '{to_tag}' tag, '{color}' color
            ),
            rebuilt_tags_colors AS (
            	SELECT expanded_tags_colors.project_id project_id, array_agg_mult(ARRAY[[expanded_tags_colors.tag, expanded_tags_colors.color]]) tags_colors
            	FROM expanded_tags_colors
            	GROUP BY expanded_tags_colors.project_id
            )

        UPDATE projects_project
        SET tags_colors = rebuilt_tags_colors.tags_colors
        FROM rebuilt_tags_colors
        WHERE projects_project.id = rebuilt_tags_colors.project_id;
    """
    sql = sql.format(project_id=project.id, from_tag=from_tag, to_tag=to_tag, color=color)
    cursor = connection.cursor()
    cursor.execute(sql)


def delete_tag(project, tag):
    sql = """
        UPDATE userstories_userstory SET tags = array_remove(tags, '{tag}') WHERE project_id={project_id};
        UPDATE tasks_task SET tags = array_remove(tags, '{tag}') WHERE project_id={project_id};
        UPDATE issues_issue SET tags = array_remove(tags, '{tag}') WHERE project_id={project_id};

        WITH
            tags_colors AS (
            	SELECT id project_id, reduce_dim(tags_colors) tags_colors
                FROM projects_project
                WHERE id = {project_id}
            ),
            rebuilt_tags_colors AS (
            	SELECT tags_colors.project_id project_id, array_agg_mult(ARRAY[[tags_colors.tags_colors[1], tags_colors.tags_colors[2]]]) tags_colors
            	FROM tags_colors
            	WHERE tags_colors.tags_colors[1] != '{tag}'
            	GROUP BY tags_colors.project_id
            )

        UPDATE projects_project
        SET tags_colors = rebuilt_tags_colors.tags_colors
        FROM rebuilt_tags_colors
        WHERE projects_project.id = rebuilt_tags_colors.project_id;
    """
    sql = sql.format(project_id=project.id, tag=tag)
    cursor = connection.cursor()
    cursor.execute(sql)


def mix_tags(project, from_tags, to_tag):
    for from_tag in from_tags:
        rename_tag(project, from_tag, to_tag)
